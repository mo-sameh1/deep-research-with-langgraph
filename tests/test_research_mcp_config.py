from pathlib import Path

from deep_research_langgraph.research_mcp.config import get_mcp_config, get_sample_files_dir


def test_sample_files_dir_contains_course_document() -> None:
    sample_dir = get_sample_files_dir()

    assert sample_dir.is_dir()
    assert (sample_dir / "coffee_shops_sf.md").is_file()


def test_mcp_config_limits_filesystem_server_to_sample_dir() -> None:
    sample_dir = Path("/tmp/example-docs")

    config = get_mcp_config(sample_dir)

    assert config["filesystem"]["command"] == "npx"
    assert config["filesystem"]["transport"] == "stdio"
    assert "@modelcontextprotocol/server-filesystem" in config["filesystem"]["args"]
    assert str(sample_dir) in config["filesystem"]["args"]
