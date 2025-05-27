"""Logging configuration for protoc-gen-py-mcp plugin using Python's logging module."""

import logging
import sys


def configure_logging(debug_mode: bool, debug_level: str) -> None:
    """Configure Python logging based on plugin debug settings.

    Args:
        debug_mode: Whether debug logging is enabled
        debug_level: Debug level (basic, verbose, trace)
    """
    # Determine logging level based on debug settings
    if not debug_mode:
        level = logging.WARNING
    else:
        level_map = {
            "basic": logging.DEBUG,  # Changed to DEBUG so debug messages show up
            "verbose": logging.DEBUG,
            "trace": logging.DEBUG,  # We'll use DEBUG for all debug levels
        }
        level = level_map.get(debug_level, logging.DEBUG)

    # Configure logging
    logging.basicConfig(
        level=level,
        format="[protoc-gen-py-mcp] %(message)s",
        stream=sys.stderr,
        force=True,  # Override any existing configuration
    )


def get_logger() -> logging.Logger:
    """Get the logger for the plugin."""
    return logging.getLogger("protoc-gen-py-mcp")
