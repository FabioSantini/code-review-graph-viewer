"""Named graph connections, persisted independently from product settings."""
import json
import threading
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator


class SourceInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    transport: Literal["http", "stdio", "local"] = "http"
    url: str = Field(default="", max_length=2048)
    command: str = Field(default="", max_length=1024)
    args: list[str] = Field(default_factory=list, max_length=40)
    repo_root: str = Field(default="", max_length=2048)
    database_path: str = Field(default="", max_length=2048)

    @model_validator(mode="after")
    def validate_connection(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("A source name is required")
        if self.transport == "http":
            url = urlsplit(self.url)
            if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
                raise ValueError("Enter an HTTP or HTTPS MCP URL without embedded credentials")
        if self.transport == "stdio" and not self.command.strip():
            raise ValueError("A local MCP command is required")
        if self.transport == "local" and not self.database_path:
            raise ValueError("A local graph index is required")
        return self


def initial_source(name, path):
    source = {"id": name, "name": name,
              "transport": "local", "database_path": str(path), "repo_root": str(path.parent.parent)}
    config = path.parent.parent / ".mcp.json"
    if config.is_file():
        entries = json.loads(config.read_text(encoding="utf-8")).get("mcpServers", {})
        entry = entries.get("code-review-graph")
        if entry:
            source.update(transport="stdio", command=entry["command"], args=entry.get("args", []))
    return source


class SourceRegistry:
    def __init__(self, path: Path, projects):
        self.path, self.lock = path, threading.RLock()
        self.items = json.loads(path.read_text(encoding="utf-8")) if path.exists() else [
            initial_source(name, database) for name, database in projects.items()]

    def all(self):
        with self.lock:
            return [dict(item) for item in self.items]

    def get(self, identity):
        for item in self.all():
            if item["id"] == identity:
                return item
        raise HTTPException(404, "Source not found")

    def save(self, value, identity=None):
        with self.lock:
            if identity:
                self.get(identity)
            item = {"id": identity or uuid4().hex[:12], **value.model_dump()}
            self.items = [old for old in self.items if old["id"] != item["id"]] + [item]
            self._persist()
            return item

    def remove(self, identity):
        with self.lock:
            self.get(identity)
            self.items = [item for item in self.items if item["id"] != identity]
            self._persist()

    def _persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.items, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
