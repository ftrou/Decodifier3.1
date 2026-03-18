import fnmatch
import json
import os
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .schemas import (
    ProjectCreate,
    SearchRequest,
    SearchResponse,
    SymbolSearchRequest,
    SymbolSearchResponse,
    ContextReadPlanRequest,
    ContextReadPlanResponse,
    MaterializeContextRequest,
    MaterializedContextResponse,
    FilePayload,
    PatchPayload,
    NotesPayload,
    PackInstallPayload,
    ProjectPacksPayload,
    ConversationCreate,
    ConversationAppend,
    ConversationState,
    ActiveConversationPayload,
)
from . import storage, indexer, files, conversation_store
from .config import DEFAULT_IGNORE
from .events import event_log
from .packs import pack_registry
from .policy import policy_engine, PolicyViolation
from decodifier.engine.routes_patterns import router as patterns_router
from decodifier import retrieval
from backend.api.generated_endpoints import router as generated_router

app = FastAPI(title="DeCodifier Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patterns_router)
app.include_router(generated_router, prefix="/api")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _load_dashboard_html() -> str:
    path = Path(__file__).resolve().parent / "static" / "dashboard.html"
    return path.read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def dashboard_root() -> HTMLResponse:
    return HTMLResponse(_load_dashboard_html())


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(_load_dashboard_html())


def _handle_policy_error(exc: PolicyViolation) -> None:
    raise HTTPException(status_code=400, detail=exc.as_dict())


def _log_policy_denied(project_id: str, *, code: str, path: str, op: str) -> None:
    event_log.append(project_id, "policy_denied", {"code": code, "path": path, "op": op})


def _ensure_policy_path(project_id: str, project_path: str, relpath: str, *, op: str) -> None:
    try:
        policy_engine.ensure_allowed_path(project_path, relpath, op=op)
    except PolicyViolation as exc:
        if op == "write":
            _log_policy_denied(project_id, code=exc.code, path=relpath, op=op)
        _handle_policy_error(exc)


def _ensure_write_size(project_id: str, relpath: str, content: str, *, op: str = "write") -> None:
    try:
        policy_engine.ensure_write_size(content)
    except PolicyViolation as exc:
        if op == "write":
            _log_policy_denied(project_id, code=exc.code, path=relpath, op=op)
        _handle_policy_error(exc)


def _matches_ignore(rel: Path, patterns: List[str]) -> bool:
    rel_str = rel.as_posix()
    parts = rel_str.split("/")
    for pattern in patterns:
        normalized = pattern.strip().lstrip("./")
        if not normalized:
            continue
        if normalized.endswith("/"):
            normalized = normalized[:-1]
        if fnmatch.fnmatch(rel_str, normalized) or rel_str.startswith(f"{normalized}/"):
            return True
        if any(fnmatch.fnmatch(part, normalized) for part in parts):
            return True
    return False


def _should_skip(rel: Path, patterns: List[str]) -> bool:
    if any(part.startswith(".") for part in rel.parts):
        return True
    return _matches_ignore(rel, patterns)


def _load_events(project_id: str) -> List[Dict[str, object]]:
    path = event_log.root / f"{project_id}.jsonl"
    if not path.exists():
        return []
    events: List[Dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


@app.get("/api/projects")
def list_projects():
    return storage.load_projects()


@app.get("/api/projects/status")
def project_status():
    projects = storage.load_projects()
    return {"status": indexer.get_status_map(projects)}


@app.post("/api/projects")
def create_project(payload: ProjectCreate):
    project = storage.add_project(payload)
    return project


@app.get("/api/projects/{project_id}/notes")
def get_notes(project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"notes": project.notes}


@app.post("/api/projects/{project_id}/notes")
def update_notes(project_id: str, payload: NotesPayload):
    project = storage.update_notes(project_id, payload.notes)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"notes": project.notes}


@app.post("/api/projects/{project_id}/index")
def index_project(project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return indexer.index_project(project)


@app.get("/api/projects/{project_id}/tree")
def get_tree(project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    root = Path(project.path)
    tree = []
    ignore_patterns = list(DEFAULT_IGNORE) + list(project.ignore or [])
    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        rel_dir = current_dir.relative_to(root)
        if rel_dir != Path(".") and _should_skip(rel_dir, ignore_patterns):
            dirnames[:] = []
            continue
        if rel_dir != Path("."):
            tree.append({"path": str(rel_dir), "is_dir": True})

        pruned = []
        for dirname in dirnames:
            rel = (current_dir / dirname).relative_to(root)
            if _should_skip(rel, ignore_patterns):
                continue
            pruned.append(dirname)
        dirnames[:] = pruned

        for filename in filenames:
            rel = (current_dir / filename).relative_to(root)
            if _should_skip(rel, ignore_patterns):
                continue
            tree.append({"path": str(rel), "is_dir": False})
    return {"tree": tree}


@app.get("/api/file")
def get_file(path: str, project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_policy_path(project.id, project.path, path, op="read")
    content = files.read_file(project.path, path)
    return {"path": path, "content": content}


@app.post("/api/file/save")
def save_file(payload: FilePayload, project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_policy_path(project.id, project.path, payload.path, op="write")
    _ensure_write_size(project.id, payload.path, payload.content)
    files.write_file(project.path, payload.path, payload.content)
    byte_len = len(payload.content.encode("utf-8", errors="ignore"))
    event_log.append(project.id, "file_saved", {"path": payload.path, "bytes": byte_len})
    return {"status": "saved"}


@app.post("/api/file/upload")
async def upload_file(project_id: str, path: str = Form(...), file: UploadFile = File(...)):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_policy_path(project.id, project.path, path, op="write")
    await files.write_upload(project.path, path, file)
    event_log.append(project.id, "file_uploaded", {"path": path, "filename": file.filename})
    return {"status": "saved"}


def _apply_patch_for_project(project_id: str, payload: PatchPayload) -> Dict[str, str]:
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_policy_path(project.id, project.path, payload.path, op="write")
    _ensure_write_size(project.id, payload.path, payload.patch)
    files.apply_patch(project.path, payload.path, payload.patch)
    event_log.append(project.id, "patch_applied", {"path": payload.path})
    return {"status": "applied"}


@app.post("/api/projects/{project_id}/file/apply_patch")
def apply_patch(project_id: str, payload: PatchPayload):
    return _apply_patch_for_project(project_id, payload)


@app.post("/api/file/apply_patch")
def apply_patch_legacy(payload: PatchPayload, project_id: str = Query(...)):
    return _apply_patch_for_project(project_id, payload)


@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest):
    project = storage.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    results = indexer.search_chunks(project.id, req.query, k=req.k)
    return SearchResponse(results=results)


@app.post("/api/search_symbols", response_model=SymbolSearchResponse)
def search_symbols(req: SymbolSearchRequest):
    project = storage.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    symbols = retrieval.search_symbols(project.path, req.query, max_symbols=req.max_symbols, ignore=project.ignore)
    return SymbolSearchResponse(symbols=symbols)


@app.post("/api/context_read_plan", response_model=ContextReadPlanResponse)
def context_read_plan(req: ContextReadPlanRequest):
    project = storage.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = retrieval.get_context_read_plan(
        project.path,
        req.query,
        max_tokens=req.max_tokens,
        max_symbols=req.max_symbols,
        max_lines=req.max_lines,
        ignore=project.ignore,
    )
    return ContextReadPlanResponse(**plan)


@app.post("/api/materialize_context", response_model=MaterializedContextResponse)
def materialize_context(req: MaterializeContextRequest):
    project = storage.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    context = retrieval.materialize_context(
        project.path,
        req.plan.model_dump(),
        max_tokens=req.max_tokens,
        max_symbols=req.max_symbols,
        max_lines=req.max_lines,
    )
    return MaterializedContextResponse(**context)


@app.get("/api/packs")
def list_packs():
    return {"packs": [pack.__dict__ for pack in pack_registry.list()]}


@app.post("/api/packs/install")
def install_pack(payload: PackInstallPayload):
    try:
        pack = pack_registry.install_from_dir(payload.path, name=payload.name, overwrite=payload.overwrite)
    except PolicyViolation as exc:
        _handle_policy_error(exc)
    return {"pack": pack.__dict__}


@app.post("/api/projects/{project_id}/packs")
def update_project_packs(project_id: str, payload: ProjectPacksPayload):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    installed = {pack.name for pack in pack_registry.list()}
    missing = [name for name in payload.packs if name not in installed]
    if missing:
        raise HTTPException(status_code=400, detail={"code": "PACK_NOT_INSTALLED", "message": f"Missing packs: {missing!r}"})
    project = storage.update_packs(project_id, payload.packs)
    return {"packs": project.packs if project else []}


@app.get("/api/projects/{project_id}/packs/specs")
def get_pack_specs(project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        specs = pack_registry.list_specs(project.packs or [])
    except PolicyViolation as exc:
        _handle_policy_error(exc)
    return {"packs": project.packs, "specs": specs}


@app.post("/api/decodifier/generate")
def generate(project_id: str):
    # TODO connect to real DeCodifier process
    # For now? Just read enabled specs and report count.
    from .packs import get_project_specs

    try:
        specs = get_project_specs(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    except PolicyViolation as exc:
        _handle_policy_error(exc)
    return {"status": "ok", "specs_found": len(specs)}


@app.get("/api/projects/{project_id}/events")
def list_events(project_id: str):
    if not storage.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"events": _load_events(project_id)}


@app.get("/api/conversations/{project_id}", response_model=ConversationState)
def list_conversations(project_id: str):
    if not storage.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    state = conversation_store.load_state_with_seed(project_id)
    return ConversationState(conversations=state["conversations"], active_id=state.get("active_id"))


@app.post("/api/conversations/{project_id}")
def create_conversation(project_id: str, payload: ConversationCreate):
    if not storage.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    state = conversation_store.ensure_conversation(project_id, payload.id, payload.title)
    state = conversation_store.set_active(project_id, payload.id)
    return state


@app.post("/api/conversations/{project_id}/append")
def append_conversation(project_id: str, payload: ConversationAppend):
    if not storage.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    conversation_store.append_message(project_id, payload.id, payload.message, payload.title or "Session")
    return conversation_store.load_state_with_seed(project_id)


@app.post("/api/conversations/{project_id}/active")
def activate_conversation(project_id: str, payload: ActiveConversationPayload):
    if not storage.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    state = conversation_store.set_active(project_id, payload.id)
    return state
