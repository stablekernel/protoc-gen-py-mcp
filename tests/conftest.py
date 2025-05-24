"""Pytest configuration and fixtures for protoc-gen-py-mcp tests."""

import pytest
import sys
from pathlib import Path

# Add the src directory to the Python path so we can import our modules
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))


@pytest.fixture(scope="session")
def plugin_installed():
    """Fixture to ensure the plugin is installed and available."""
    import subprocess
    
    # Check if protoc-gen-py-mcp is available
    try:
        result = subprocess.run(
            ["which", "protoc-gen-py-mcp"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Try to install in development mode
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-e", "."
            ], check=True, cwd=Path(__file__).parent.parent)
    except Exception:
        pytest.skip("Could not install or find protoc-gen-py-mcp plugin")


@pytest.fixture
def temp_project():
    """Fixture that provides a temporary project for testing."""
    from tests.test_utils import TempProtoProject
    
    with TempProtoProject() as project:
        yield project