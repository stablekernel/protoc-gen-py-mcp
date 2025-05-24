"""CLI entry point for protoc-gen-py-mcp plugin."""

from ..plugin import main as plugin_main


def main() -> None:
    """Entry point for the CLI."""
    plugin_main()
