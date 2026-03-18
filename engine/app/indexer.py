import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .schemas import Project
from .config import get_settings
from .paths import data_root

_client = None
_observers: Dict[str, Observer] = {}
_embedder = None
_index_status: Dict[str, Dict[str, str]] = {}


def _token_chunks(text: str, max_chars: int = 1200, overlap: int = 120) -> Iterable[Dict[str, Any]]:
    lines = text.splitlines()
    buffer: List[str] = []
    char_count = 0
    start_line = 1
    for idx, line in enumerate(lines, start=1):
        if char_count + len(line) > max_chars and buffer:
            yield {"text": "\n".join(buffer), "start": start_line, "end": idx - 1}
            # keep small overlap
            keep = max(0, int(overlap / max(len(line), 1)))
            buffer = buffer[-keep:]
            char_count = sum(len(l) for l in buffer)
            start_line = max(1, idx - keep)
        buffer.append(line)
        char_count += len(line)
    if buffer:
        yield {"text": "\n".join(buffer), "start": start_line, "end": len(lines)}


def _combined_ignore(project: Project) -> List[str]:
    combined = []
    settings = get_settings()
    for entry in list(settings.default_ignore) + list(project.ignore or []):
        if entry not in combined:
            combined.append(entry)
    return combined


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


def _should_skip(path: Path, project: Project, patterns: List[str] | None = None) -> bool:
    rel = path.relative_to(Path(project.path))
    ignore_patterns = patterns or _combined_ignore(project)
    if _matches_ignore(rel, ignore_patterns):
        return True
    if path.is_dir():
        return False
    allowed_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".cpp", ".md", ".rs", ".java"}
    return path.suffix not in allowed_suffixes


def _get_vector_root() -> Path:
    vector_root = data_root() / "chroma"
    vector_root.mkdir(parents=True, exist_ok=True)
    return vector_root


def _get_client():
    global _client
    if _client is None:
        import chromadb
        from chromadb.config import Settings

        _client = chromadb.PersistentClient(
            path=str(_get_vector_root()),
            settings=Settings(allow_reset=False, anonymized_telemetry=False),
        )
    return _client


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(get_settings().embedding_model)
    return _embedder


def _embed(texts: List[str]) -> List[List[float]]:
    return _get_embedder().encode(texts, normalize_embeddings=True).tolist()


def index_project(project: Project) -> Dict[str, Any]:
    _index_status[project.id] = {
        "state": "indexing",
        "note": "Indexing...",
        "updated_at": datetime.utcnow().isoformat(),
    }
    root = Path(project.path)
    collection = _get_client().get_or_create_collection(name=project.id, metadata={"project": project.name})
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []
    ignore_patterns = _combined_ignore(project)
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            current_dir = Path(dirpath)
            pruned = []
            for dirname in dirnames:
                rel_dir = (current_dir / dirname).relative_to(root)
                if _matches_ignore(rel_dir, ignore_patterns):
                    continue
                pruned.append(dirname)
            dirnames[:] = pruned

            for filename in filenames:
                path = current_dir / filename
                if _should_skip(path, project, ignore_patterns):
                    continue
                rel = str(path.relative_to(root))
                text = path.read_text(encoding="utf-8", errors="ignore")
                for chunk_idx, chunk in enumerate(_token_chunks(text)):
                    chunk_id = f"{rel}:{chunk_idx}"
                    ids.append(chunk_id)
                    docs.append(chunk["text"])
                    metas.append(
                        {
                            "file_path": rel,
                            "start": chunk["start"],
                            "end": chunk["end"],
                            "modified": path.stat().st_mtime,
                        }
                    )
        if docs:
            embeddings = _embed(docs)
            collection.upsert(documents=docs, ids=ids, metadatas=metas, embeddings=embeddings)
        _index_status[project.id] = {
            "state": "indexed",
            "note": f"Indexed {len(docs)} chunks",
            "updated_at": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        _index_status[project.id] = {
            "state": "error",
            "note": str(exc),
            "updated_at": datetime.utcnow().isoformat(),
        }
        raise
    _start_watcher(project)
    return {"project_id": project.id, "chunks_indexed": len(docs)}


def search_chunks(project_id: str, query: str, k: int = 12) -> List[Dict[str, Any]]:
    try:
        collection = _get_client().get_collection(name=project_id)
    except Exception:
        return []
    embedding = _embed([query])[0]
    res = collection.query(query_embeddings=[embedding], n_results=k)
    hits = []
    for doc, meta in zip(res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]):
        hits.append({"text": doc, "meta": meta})
    return hits


class _ChangeHandler(FileSystemEventHandler):
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.ignore_patterns = _combined_ignore(project)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._reindex_file(Path(event.src_path))

    def on_created(self, event):
        if event.is_directory:
            return
        self._reindex_file(Path(event.src_path))

    def _reindex_file(self, path: Path):
        if _should_skip(path, self.project, self.ignore_patterns):
            return
        root = Path(self.project.path)
        rel = str(path.relative_to(root))
        collection = _get_client().get_or_create_collection(name=self.project.id)
        text = path.read_text(encoding="utf-8", errors="ignore")
        docs: List[str] = []
        ids: List[str] = []
        metas: List[Dict[str, Any]] = []
        for chunk_idx, chunk in enumerate(_token_chunks(text)):
            chunk_id = f"{rel}:{chunk_idx}"
            ids.append(chunk_id)
            docs.append(chunk["text"])
            metas.append(
                {
                    "file_path": rel,
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "modified": path.stat().st_mtime,
                }
            )
        if docs:
            embeddings = _embed(docs)
            collection.upsert(documents=docs, ids=ids, metadatas=metas, embeddings=embeddings)


def _start_watcher(project: Project) -> None:
    if project.id in _observers:
        return
    handler = _ChangeHandler(project)
    observer = Observer()
    observer.schedule(handler, path=str(project.path), recursive=True)
    observer.daemon = True
    observer.start()
    _observers[project.id] = observer


def get_status_map(projects: List[Project]) -> Dict[str, Dict[str, str]]:
    status = {}
    for project in projects:
        status[project.id] = _index_status.get(
            project.id,
            {"state": "indexed", "note": "Indexed", "updated_at": None},
        )
    return status
