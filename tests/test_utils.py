"""Test utilities for protoc-gen-py-mcp tests."""

import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf import descriptor_pb2


def run_protoc_with_plugin(
    proto_files: List[Path],
    output_dir: Path,
    include_dirs: Optional[List[Path]] = None,
    plugin_path: Optional[Path] = None
) -> subprocess.CompletedProcess:
    """
    Run protoc with the py-mcp plugin.
    
    Args:
        proto_files: List of proto files to process
        output_dir: Directory to write generated files
        include_dirs: Additional include directories
        plugin_path: Path to the plugin executable (auto-detected if None)
        
    Returns:
        subprocess.CompletedProcess with the result
    """
    if plugin_path is None:
        # Use the installed protoc-gen-py-mcp command
        plugin_path = "protoc-gen-py-mcp"
    
    cmd = [
        "python", "-m", "grpc_tools.protoc",
        f"--py-mcp_out={output_dir}",
    ]
    
    # Add include directories
    if include_dirs:
        for include_dir in include_dirs:
            cmd.extend(["-I", str(include_dir)])
    
    # Add proto files
    cmd.extend(str(f) for f in proto_files)
    
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=output_dir.parent
    )


def create_test_proto_request(proto_content: str, filename: str = "test.proto") -> plugin.CodeGeneratorRequest:
    """
    Create a CodeGeneratorRequest for testing from proto content.
    
    Args:
        proto_content: The proto file content as a string
        filename: The filename for the proto file
        
    Returns:
        A CodeGeneratorRequest that can be passed to the plugin
    """
    # This is a simplified version - in real tests we'd parse the proto properly
    # For now, we'll create a minimal request structure
    request = plugin.CodeGeneratorRequest()
    request.file_to_generate.append(filename)
    
    # Create a basic FileDescriptorProto
    file_proto = request.proto_file.add()
    file_proto.name = filename
    file_proto.package = "test.v1"
    file_proto.syntax = "proto3"
    
    return request


def assert_valid_python_code(code: str) -> None:
    """
    Assert that the given code is valid Python by compiling it.
    
    Args:
        code: Python code string to validate
        
    Raises:
        AssertionError: If the code is not valid Python
    """
    try:
        compile(code, '<test>', 'exec')
    except SyntaxError as e:
        raise AssertionError(f"Generated code is not valid Python: {e}")


def mock_pb2_imports(code: str) -> str:
    """
    Replace pb2 module imports with mock assignments for testing.
    
    Args:
        code: Python code string with imports
        
    Returns:
        Modified code with mocked imports
    """
    code_lines = code.split('\n')
    for i, line in enumerate(code_lines):
        if line.startswith('import ') and '_pb2' in line:
            module_name = line.split()[-1]  # Get the module name
            code_lines[i] = f"{module_name} = type('MockModule', (), {{}})()  # Mock module"
    
    return '\n'.join(code_lines)


def assert_imports_successfully(code: str, globals_dict: Optional[Dict] = None) -> Dict:
    """
    Assert that the given code can be imported/executed successfully.
    
    Args:
        code: Python code string to execute
        globals_dict: Global namespace for execution
        
    Returns:
        The locals dictionary after execution
        
    Raises:
        AssertionError: If the code cannot be executed
    """
    if globals_dict is None:
        globals_dict = {}
    
    locals_dict = {}
    
    try:
        exec(code, globals_dict, locals_dict)
        return locals_dict
    except Exception as e:
        raise AssertionError(f"Generated code cannot be executed: {e}")


class TempProtoProject:
    """Context manager for creating temporary proto projects for testing."""
    
    def __init__(self):
        self.temp_dir = None
        self.proto_dir = None
        self.output_dir = None
    
    def __enter__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.proto_dir = self.temp_dir / "protos"
        self.output_dir = self.temp_dir / "generated"
        
        self.proto_dir.mkdir()
        self.output_dir.mkdir()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def add_proto_file(self, filename: str, content: str) -> Path:
        """Add a proto file to the project."""
        proto_file = self.proto_dir / filename
        proto_file.write_text(content)
        return proto_file
    
    def run_plugin(self, proto_files: Optional[List[str]] = None) -> subprocess.CompletedProcess:
        """Run the plugin on the proto files."""
        if proto_files is None:
            proto_files = list(self.proto_dir.glob("*.proto"))
        else:
            proto_files = [self.proto_dir / f for f in proto_files]
        
        return run_protoc_with_plugin(
            proto_files=proto_files,
            output_dir=self.output_dir,
            include_dirs=[self.proto_dir]
        )
    
    def get_generated_file(self, filename: str) -> Path:
        """Get path to a generated file."""
        return self.output_dir / filename
    
    def read_generated_file(self, filename: str) -> str:
        """Read the content of a generated file."""
        return self.get_generated_file(filename).read_text()