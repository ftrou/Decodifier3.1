import requests
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .errors import DeCodifierError


@dataclass
class DeCodifierClient:
    """
    Tiny HTTP client for the DeCodifier backend.

    Point this at your running FastAPI app, e.g. base_url="http://127.0.0.1:8000".
    """

    base_url: str = "http://127.0.0.1:8000"

    def _get(self, route: str, **params) -> Any:
        url = f"{self.base_url}{route}"
        resp = requests.get(url, params=params)
        if resp.status_code >= 400:
            raise DeCodifierError(
                f"GET {route} failed: {resp.status_code}",
                status_code=resp.status_code,
                payload=self._safe_json(resp),
            )
        return self._safe_json(resp)

    def _post(self, path: str, json: Optional[Dict] = None, **params) -> Any:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, params=params, json=json)
        if resp.status_code >= 400:
            raise DeCodifierError(
                f"POST {path} failed: {resp.status_code}",
                status_code=resp.status_code,
                payload=self._safe_json(resp),
            )
        return self._safe_json(resp)

    def _post_multipart(self, path: str, *, data: Dict[str, Any], files: Dict[str, Any], **params) -> Any:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, params=params, data=data, files=files)
        if resp.status_code >= 400:
            raise DeCodifierError(
                f"POST {path} failed: {resp.status_code}",
                status_code=resp.status_code,
                payload=self._safe_json(resp),
            )
        return self._safe_json(resp)

    @staticmethod
    def _safe_json(resp: requests.Response) -> Any:
        try:
            return resp.json()
        except Exception:
            return resp.text

    # Projects

    def list_projects(self) -> List[Dict[str, Any]]:
        """GET /api/projects"""
        data = self._get("/api/projects")
        return data if isinstance(data, list) else data.get("projects", [])

    def create_project(
        self,
        name: str,
        path: str,
        ignore: Optional[List[str]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /api/projects"""
        payload: Dict[str, Any] = {
            "name": name,
            "path": path,
            "ignore": ignore or [],
        }
        if project_id is not None:
            payload["id"] = project_id
        return self._post("/api/projects", json=payload)

    def get_project_tree(self, project_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """GET /api/projects/{project_id}/tree"""
        return self._get(f"/api/projects/{project_id}/tree", max_depth=max_depth)

    # Files

    def read_file(self, project_id: str, path: str) -> Dict[str, Any]:
        """GET /api/file?project_id=...&path=..."""
        return self._get("/api/file", project_id=project_id, path=path)

    def save_file(self, project_id: str, path: str, content: str) -> Dict[str, Any]:
        """
        POST /api/file/save?project_id=...

        This is the safe entry point for LLMs to write files. Policy errors
        (PATH_TRAVERSAL, IGNORED_PATH, etc.) come back as structured JSON.
        """
        payload = {"path": path, "content": content}
        return self._post("/api/file/save", json=payload, project_id=project_id)

    def upload_file(
        self,
        project_id: str,
        path: str,
        content: bytes,
        filename: str = "upload.bin",
    ) -> Dict[str, Any]:
        """POST /api/file/upload"""
        return self._post_multipart(
            "/api/file/upload",
            data={"path": path},
            files={"file": (filename, content)},
            project_id=project_id,
        )

    def apply_patch(self, project_id: str, path: str, patch: str) -> Dict[str, Any]:
        """POST /api/file/apply_patch?project_id=..."""
        payload = {"path": path, "patch": patch}
        return self._post("/api/file/apply_patch", json=payload, project_id=project_id)

    # Packs

    def list_packs(self) -> Dict[str, Any]:
        """GET /api/packs"""
        return self._get("/api/packs")

    def enable_packs_for_project(self, project_id: str, packs: List[str]) -> Dict[str, Any]:
        """POST /api/projects/{project_id}/packs"""
        return self._post(f"/api/projects/{project_id}/packs", json={"packs": packs})

    def get_pack_specs_for_project(self, project_id: str) -> Dict[str, Any]:
        """GET /api/projects/{project_id}/packs/specs"""
        return self._get(f"/api/projects/{project_id}/packs/specs")

    # Events / audit

    def get_project_events(self, project_id: str, limit: int = 50) -> Dict[str, Any]:
        """GET /api/projects/{project_id}/events"""
        return self._get(f"/api/projects/{project_id}/events", limit=limit)

    # Retrieval

    def search_symbols(self, project_id: str, query: str, max_symbols: int = 10) -> Dict[str, Any]:
        """POST /api/search_symbols"""
        return self._post(
            "/api/search_symbols",
            json={"project_id": project_id, "query": query, "max_symbols": max_symbols},
        )

    def get_context_read_plan(
        self,
        project_id: str,
        query: str,
        *,
        max_tokens: int = 800,
        max_symbols: int = 5,
        max_lines: int = 120,
    ) -> Dict[str, Any]:
        """POST /api/context_read_plan"""
        return self._post(
            "/api/context_read_plan",
            json={
                "project_id": project_id,
                "query": query,
                "max_tokens": max_tokens,
                "max_symbols": max_symbols,
                "max_lines": max_lines,
            },
        )

    def materialize_context(
        self,
        project_id: str,
        plan: Dict[str, Any],
        *,
        max_tokens: Optional[int] = None,
        max_symbols: Optional[int] = None,
        max_lines: Optional[int] = None,
    ) -> Dict[str, Any]:
        """POST /api/materialize_context"""
        payload: Dict[str, Any] = {"project_id": project_id, "plan": plan}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if max_symbols is not None:
            payload["max_symbols"] = max_symbols
        if max_lines is not None:
            payload["max_lines"] = max_lines
        return self._post("/api/materialize_context", json=payload)


def handle_decodifier_tool_call(
    client: DeCodifierClient,
    tool_name: str,
    arguments: Dict[str, Any],
) -> Any:
    """
    Dispatch a tool call from an LLM into the DeCodifier backend.

    `tool_name` should match the JSON tool name (e.g. "decodifier_list_projects"),
    and `arguments` is the parsed JSON arguments from the model.
    """

    if tool_name == "decodifier_list_projects":
        return client.list_projects()

    if tool_name == "decodifier_create_project":
        return client.create_project(
            name=arguments["name"],
            path=arguments["path"],
            ignore=arguments.get("ignore"),
            project_id=arguments.get("id"),
        )

    if tool_name == "decodifier_get_project_tree":
        return client.get_project_tree(
            project_id=arguments["project_id"],
            max_depth=arguments.get("max_depth", 5),
        )

    if tool_name == "decodifier_read_file":
        # Defensive guard so bad tool calls don't crash the demo.
        if "path" not in arguments or not arguments.get("path"):
            return {
                "error": "missing_path",
                "message": "decodifier_read_file requires a 'path' argument.",
                "received_arguments": arguments,
            }

        return client.read_file(
            project_id=arguments["project_id"],
            path=arguments["path"],
        )

    if tool_name == "decodifier_save_file":
        return client.save_file(
            project_id=arguments["project_id"],
            path=arguments["path"],
            content=arguments["content"],
        )

    if tool_name == "decodifier_upload_file":
        content = arguments.get("content", "")
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = bytes(content)
        return client.upload_file(
            project_id=arguments["project_id"],
            path=arguments["path"],
            content=content_bytes,
            filename=arguments.get("filename", "upload.bin"),
        )

    if tool_name == "decodifier_apply_patch":
        return client.apply_patch(
            project_id=arguments["project_id"],
            path=arguments["path"],
            patch=arguments["patch"],
        )

    if tool_name == "decodifier_list_packs":
        return client.list_packs()

    if tool_name == "decodifier_enable_packs_for_project":
        return client.enable_packs_for_project(
            project_id=arguments["project_id"],
            packs=arguments["packs"],
        )

    if tool_name == "decodifier_get_pack_specs_for_project":
        return client.get_pack_specs_for_project(
            project_id=arguments["project_id"],
        )

    if tool_name == "decodifier_get_project_events":
        return client.get_project_events(
            project_id=arguments["project_id"],
            limit=arguments.get("limit", 50),
        )

    if tool_name == "decodifier_search_symbols":
        return client.search_symbols(
            project_id=arguments["project_id"],
            query=arguments["query"],
            max_symbols=arguments.get("max_symbols", 10),
        )

    if tool_name == "decodifier_get_context_read_plan":
        return client.get_context_read_plan(
            project_id=arguments["project_id"],
            query=arguments["query"],
            max_tokens=arguments.get("max_tokens", 800),
            max_symbols=arguments.get("max_symbols", 5),
            max_lines=arguments.get("max_lines", 120),
        )

    if tool_name == "decodifier_materialize_context":
        return client.materialize_context(
            project_id=arguments["project_id"],
            plan=arguments["plan"],
            max_tokens=arguments.get("max_tokens"),
            max_symbols=arguments.get("max_symbols"),
            max_lines=arguments.get("max_lines"),
        )

    raise DeCodifierError(f"Unknown DeCodifier tool: {tool_name}")
