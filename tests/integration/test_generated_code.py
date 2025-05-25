"""Tests for generated MCP server code functionality."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.test_utils import TempProtoProject, assert_imports_successfully, mock_pb2_imports


class TestGeneratedCodeFunctionality:
    """Test that generated MCP server code actually works."""

    def test_generated_code_imports(self):
        """Test that generated code can be imported successfully."""
        proto_content = """
syntax = "proto3";

package test.import;

message ImportRequest {
  string name = 1;
}

message ImportResponse {
  string result = 1;
}

service ImportService {
  rpc DoImport(ImportRequest) returns (ImportResponse) {}
}
"""

        with TempProtoProject() as project:
            # Generate standard pb2 files first
            project.add_proto_file("import.proto", proto_content)

            # Generate pb2 files
            cmd_pb2 = [
                "python",
                "-m",
                "grpc_tools.protoc",
                f"--python_out={project.output_dir}",
                f"-I{project.proto_dir}",
                str(project.proto_dir / "import.proto"),
            ]
            import subprocess

            subprocess.run(cmd_pb2, check=True)

            # Generate MCP files
            result = project.run_plugin(["import.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"

            # Read the generated MCP code
            mcp_code = project.read_generated_file("import_pb2_mcp.py")

            # Mock the pb2 imports
            mcp_code = mock_pb2_imports(mcp_code)
            # Also mock the fastmcp import
            mcp_code = mcp_code.replace(
                "from fastmcp import FastMCP", "# from fastmcp import FastMCP"
            )

            # Mock the required imports
            mock_fastmcp = MagicMock()
            mock_fastmcp_instance = MagicMock()
            mock_fastmcp.return_value = mock_fastmcp_instance

            mock_globals = {
                "Optional": type(None),
                "FastMCP": mock_fastmcp,
                "grpc": MagicMock(),
            }

            # Try to execute the generated code
            locals_dict = assert_imports_successfully(mcp_code, mock_globals)

            # Check that a global mcp instance exists
            assert "mcp" in locals_dict
            assert locals_dict["mcp"] == mock_fastmcp_instance
            # The mock will be called so verify it was instantiated
            mock_fastmcp.assert_called_once_with("MCP Server from Proto")

    def test_global_mcp_instance_creation(self):
        """Test that generated code creates a global FastMCP instance."""
        proto_content = """
syntax = "proto3";

package test.instance;

message InstanceRequest {
  string input = 1;
}

message InstanceResponse {
  string output = 1;
}

service InstanceService {
  rpc ProcessInstance(InstanceRequest) returns (InstanceResponse) {}
}
"""

        with TempProtoProject() as project:
            project.add_proto_file("instance.proto", proto_content)

            # Generate pb2 files
            cmd_pb2 = [
                "python",
                "-m",
                "grpc_tools.protoc",
                f"--python_out={project.output_dir}",
                f"-I{project.proto_dir}",
                str(project.proto_dir / "instance.proto"),
            ]
            import subprocess

            subprocess.run(cmd_pb2, check=True)

            # Generate MCP files
            result = project.run_plugin(["instance.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"

            # Read the generated code
            mcp_code = project.read_generated_file("instance_pb2_mcp.py")

            # Mock the pb2 imports
            mcp_code = mock_pb2_imports(mcp_code)
            # Also mock the fastmcp import
            mcp_code = mcp_code.replace(
                "from fastmcp import FastMCP", "# from fastmcp import FastMCP"
            )

            # Mock FastMCP and dependencies
            mock_fastmcp = MagicMock()
            mock_fastmcp_instance = MagicMock()
            mock_fastmcp.return_value = mock_fastmcp_instance

            mock_globals = {
                "Optional": type(None),
                "FastMCP": mock_fastmcp,
                "grpc": MagicMock(),
            }

            # Execute the generated code
            locals_dict = assert_imports_successfully(mcp_code, mock_globals)

            # Check that global mcp instance was created
            assert "mcp" in locals_dict

            # Verify FastMCP was instantiated with the default name
            mock_fastmcp.assert_called_once_with("MCP Server from Proto")

            # Verify the global instance exists
            assert locals_dict["mcp"] == mock_fastmcp_instance

    def test_tool_function_registration(self):
        """Test that tool functions are properly registered with MCP decorators."""
        proto_content = """
syntax = "proto3";

package test.tools;

message ToolRequest {
  string name = 1;
  int32 value = 2;
}

message ToolResponse {
  bool success = 1;
}

service ToolService {
  rpc ExecuteTool(ToolRequest) returns (ToolResponse) {}
  rpc AnotherTool(ToolRequest) returns (ToolResponse) {}
}
"""

        with TempProtoProject() as project:
            project.add_proto_file("tools.proto", proto_content)

            # Generate pb2 files
            cmd_pb2 = [
                "python",
                "-m",
                "grpc_tools.protoc",
                f"--python_out={project.output_dir}",
                f"-I{project.proto_dir}",
                str(project.proto_dir / "tools.proto"),
            ]
            import subprocess

            subprocess.run(cmd_pb2, check=True)

            # Generate MCP files
            result = project.run_plugin(["tools.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"

            # Read the generated code
            mcp_code = project.read_generated_file("tools_pb2_mcp.py")

            # Mock the pb2 imports
            mcp_code = mock_pb2_imports(mcp_code)

            # Mock FastMCP with tool decorator
            mock_fastmcp_instance = MagicMock()
            mock_tool_decorator = MagicMock()
            mock_fastmcp_instance.tool.return_value = mock_tool_decorator

            mock_fastmcp = MagicMock()
            mock_fastmcp.return_value = mock_fastmcp_instance

            mock_globals = {
                "Optional": type(None),
                "FastMCP": mock_fastmcp,
                "grpc": MagicMock(),
            }

            # Execute the generated code
            locals_dict = assert_imports_successfully(mcp_code, mock_globals)

            # Verify that the global mcp instance exists
            assert "mcp" in locals_dict

            # Verify that tool functions were registered by checking the generated code
            # The tool decorator calls should happen during execution
            assert "execute_tool" in mcp_code
            assert "another_tool" in mcp_code
            assert "@mcp.tool" in mcp_code

    def test_parameter_type_hints(self):
        """Test that generated functions have correct parameter type hints."""
        proto_content = """
syntax = "proto3";

package test.types;

message TypesRequest {
  string name = 1;
  int32 count = 2;
  bool enabled = 3;
  repeated string tags = 4;
  optional string description = 5;
  map<string, string> metadata = 6;
}

message TypesResponse {
  bool success = 1;
}

service TypesService {
  rpc TestTypes(TypesRequest) returns (TypesResponse) {}
}
"""

        with TempProtoProject() as project:
            project.add_proto_file("types.proto", proto_content)

            # Generate MCP files
            result = project.run_plugin(["types.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"

            # Read and check the generated code
            mcp_code = project.read_generated_file("types_pb2_mcp.py")

            # Check for correct type hints in the function signature
            assert "name: str" in mcp_code
            assert "count: int" in mcp_code
            assert "enabled: bool" in mcp_code
            # Uses typing.Optional instead of union syntax
            assert "tags: list[str]" in mcp_code or "tags: List[str]" in mcp_code
            assert "description: Optional[str] = None" in mcp_code
            assert "metadata: dict[str, str]" in mcp_code or "metadata: Dict[str, str]" in mcp_code

            # Check for minimal imports
            assert "from typing import Optional" in mcp_code

    def test_oneof_field_handling(self):
        """Test that oneof fields are properly handled in generated code."""
        proto_content = """
syntax = "proto3";

package test.oneof;

message OneofRequest {
  string id = 1;

  oneof action {
    string create = 2;
    string update = 3;
    bool delete = 4;
  }
}

message OneofResponse {
  bool success = 1;
}

service OneofService {
  rpc HandleOneof(OneofRequest) returns (OneofResponse) {}
}
"""

        with TempProtoProject() as project:
            project.add_proto_file("oneof.proto", proto_content)

            # Generate MCP files
            result = project.run_plugin(["oneof.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"

            # Read and check the generated code
            mcp_code = project.read_generated_file("oneof_pb2_mcp.py")

            # Check that oneof fields are optional
            assert "create: Optional[str] = None" in mcp_code
            assert "update: Optional[str] = None" in mcp_code
            assert "delete: Optional[bool] = None" in mcp_code

            # Check for oneof validation comment
            assert "# Oneof validation:" in mcp_code
            assert "Only one of [create, update, delete] should be provided" in mcp_code

            # Check for conditional field assignment
            assert "if create is not None:" in mcp_code
            assert "request.create = create" in mcp_code

    def test_json_serialization(self):
        """Test that generated code uses proper JSON serialization."""
        proto_content = """
syntax = "proto3";

package test.json;

message JsonRequest {
  string input = 1;
}

message JsonResponse {
  string output = 1;
}

service JsonService {
  rpc ConvertJson(JsonRequest) returns (JsonResponse) {}
}
"""

        with TempProtoProject() as project:
            project.add_proto_file("json.proto", proto_content)

            # Generate MCP files
            result = project.run_plugin(["json.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"

            # Read and check the generated code
            mcp_code = project.read_generated_file("json_pb2_mcp.py")

            # Check for direct gRPC calls
            assert "stub = json_pb2_grpc.JsonServiceStub(channel)" in mcp_code
            assert "response = stub.ConvertJson(request)" in mcp_code
            assert "return result" in mcp_code  # Generated code returns response as dict
            assert "MessageToDict(response)" in mcp_code  # Converts protobuf to dict

            # Check that request construction is present
            assert "request = json_pb2.JsonRequest()" in mcp_code
