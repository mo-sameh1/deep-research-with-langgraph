"""MCP filesystem configuration for local document research."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from langchain_mcp_adapters.client import MultiServerMCPClient


def get_sample_files_dir() -> Path:
    """Return the directory exposed to the filesystem MCP server."""

    return Path(__file__).resolve().parent / "files"


def get_mcp_config(files_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return the MCP stdio server config for filesystem access."""

    resolved_files_dir = (files_dir or get_sample_files_dir()).resolve()
    return {
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(resolved_files_dir),
            ],
            "transport": "stdio",
        }
    }


def create_mcp_client(files_dir: Path | None = None) -> MultiServerMCPClient:
    """Create an MCP client for the configured local filesystem server."""

    return MultiServerMCPClient(cast(Any, get_mcp_config(files_dir)))


__all__ = ["create_mcp_client", "get_mcp_config", "get_sample_files_dir"]
