# CLAUDE.md - Code Style and Conventions for protoc-gen-py-mcp

This document outlines the coding standards and conventions for the protoc-gen-py-mcp project. Follow these guidelines when contributing code.

## Project Structure

- Use `src/` layout for the main package source code
- Keep examples and generated code in `protos/` directory
- Place executable scripts at the project root level
- Use `pyproject.toml` for all project configuration

## Python Code Style

### Import Organization
```python
# 1. Standard library imports (alphabetical)
import argparse
import sys

# 2. Third-party imports (alphabetical)
import grpc
from google.protobuf import descriptor_pb2

# 3. Local imports (alphabetical)
from protos import example_pb2
```

### Naming Conventions
- **Functions and variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private/internal**: `_leading_underscore`
- **Generated files**: Use consistent suffixes (`_pb2.py`, `_pb2_grpc.py`, `_pb2_mcp.py`)

### Type Hints
- Always include return type annotations for functions
- Use type hints for function parameters
- Include type stub files (`.pyi`) for generated code
```python
def main() -> None:
    """Main entry point."""
    pass

def process_request(vibe: str, user_id: int) -> dict:
    """Process a user request."""
    return {}
```

### Docstrings
- Use triple double quotes (`"""`) for all docstrings
- Include module-level docstrings for all Python files
- Keep docstrings concise but descriptive
```python
"""Protoc generator for Python MCP servers."""

def main() -> None:
    """Main entry point for the CLI."""
    pass
```

### Code Organization
- Use `if __name__ == '__main__':` pattern for executable modules
- Keep functions focused and single-purpose
- Use 4-space indentation consistently
- Prefer f-strings for string formatting where appropriate

## Dependencies and Frameworks

### Core Dependencies
- Use `fastmcp>=2.3.1` for MCP server functionality
- Use `protobuf>=6.30.2` for protocol buffer handling
- Require Python 3.10+

### Development Tools
- Use `pyright` for type checking with basic mode
- Use `pytest` for testing with asyncio support
- Use `uv` for dependency management

## File and Directory Conventions

### Source Code
- Main package code goes in `src/protoc_gen_py_mcp/`
- CLI modules go in `src/protoc_gen_py_mcp/cli/`
- Include `__init__.py` files with appropriate docstrings

### Generated Code
- Place proto files and generated code in `protos/` directory
- Use consistent naming: `example.proto` → `example_pb2.py`, `example_pb2_grpc.py`, `example_pb2_mcp.py`
- Include type stub files for all generated Python modules

## Configuration Files

### pyproject.toml
- Use `hatchling` as the build backend
- Include dynamic versioning with `uv-dynamic-versioning`
- Configure development dependencies in `[project.optional-dependencies]`
- Register console scripts in `[project.scripts]`

### Makefile
- Use `.PHONY` declarations for non-file targets
- Define clear variables for common paths and tools
- Group related targets logically

## Code Generation Patterns

### Plugin Development
- Follow protoc plugin protocol standards
- Use systematic descriptor parsing
- Generate code with proper indentation and organization
- Include clear placeholder comments for implementation

### MCP Integration
- Use decorator-based tool registration pattern
- Follow FastMCP conventions for async functions
- Include proper type hints for MCP tool parameters

## Error Handling and Logging

- Use minimal but appropriate error handling
- Include meaningful error messages
- Avoid excessive try/catch blocks for normal flow control

## Testing

- Write tests for public APIs
- Use async test patterns where appropriate
- Test both success and error cases
- Include integration tests for generated code

## Documentation

- Keep README.md updated with installation and usage instructions
- Document any new CLI arguments or options
- Include examples of generated code patterns
- Update requirements documentation as needed

## Git and Version Control

- Use meaningful commit messages
- Avoid committing generated files unless they're examples
- Keep the repository clean of temporary files

## Performance Considerations

- Use appropriate data structures for protobuf handling
- Avoid unnecessary string concatenations in tight loops
- Consider memory usage when processing large proto files

---

When in doubt, follow the existing patterns in the codebase. Look at similar implementations in `src/protoc_gen_py_mcp/` and `protos/` for guidance.