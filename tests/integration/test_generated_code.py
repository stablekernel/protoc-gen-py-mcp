"""Tests for generated MCP server code functionality."""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

from tests.test_utils import TempProtoProject, assert_imports_successfully, mock_pb2_imports


class TestGeneratedCodeFunctionality:
    """Test that generated MCP server code actually works."""
    
    def test_generated_code_imports(self):
        """Test that generated code can be imported successfully."""
        proto_content = '''
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
'''
        
        with TempProtoProject() as project:
            # Generate standard pb2 files first
            project.add_proto_file("import.proto", proto_content)
            
            # Generate pb2 files
            cmd_pb2 = [
                "python", "-m", "grpc_tools.protoc",
                f"--python_out={project.output_dir}",
                f"-I{project.proto_dir}",
                str(project.proto_dir / "import.proto")
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
            
            # Mock the required imports
            mock_globals = {
                'List': list,
                'Dict': dict,
                'Optional': type(None),
                'Any': object,
                'FastMCP': MagicMock,
                'json_format': MagicMock(),
            }
            
            # Try to execute the generated code
            locals_dict = assert_imports_successfully(mcp_code, mock_globals)
            
            # Check that the server factory function exists
            assert 'create_importservice_server' in locals_dict
            assert callable(locals_dict['create_importservice_server'])
    
    def test_server_factory_creation(self):
        """Test that server factory functions create FastMCP instances."""
        proto_content = '''
syntax = "proto3";

package test.factory;

message FactoryRequest {
  string input = 1;
}

message FactoryResponse {
  string output = 1;
}

service FactoryService {
  rpc ProcessFactory(FactoryRequest) returns (FactoryResponse) {}
}
'''
        
        with TempProtoProject() as project:
            project.add_proto_file("factory.proto", proto_content)
            
            # Generate pb2 files
            cmd_pb2 = [
                "python", "-m", "grpc_tools.protoc",
                f"--python_out={project.output_dir}",
                f"-I{project.proto_dir}",
                str(project.proto_dir / "factory.proto")
            ]
            import subprocess
            subprocess.run(cmd_pb2, check=True)
            
            # Generate MCP files
            result = project.run_plugin(["factory.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Read the generated code
            mcp_code = project.read_generated_file("factory_pb2_mcp.py")
            
            # Mock the pb2 imports
            mcp_code = mock_pb2_imports(mcp_code)
            
            # Mock FastMCP and dependencies
            mock_fastmcp = MagicMock()
            mock_fastmcp_instance = MagicMock()
            mock_fastmcp.return_value = mock_fastmcp_instance
            
            mock_globals = {
                'List': list,
                'Dict': dict,  
                'Optional': type(None),
                'Any': object,
                'FastMCP': mock_fastmcp,
                'json_format': MagicMock(),
            }
            
            # Execute the generated code
            locals_dict = assert_imports_successfully(mcp_code, mock_globals)
            
            # Call the server factory function
            server_factory = locals_dict['create_factoryservice_server']
            result = server_factory()
            
            # Verify FastMCP was instantiated with the service name
            mock_fastmcp.assert_called_once_with("FactoryService")
            
            # Verify the factory returns the FastMCP instance
            assert result == mock_fastmcp_instance
    
    def test_tool_function_registration(self):
        """Test that tool functions are properly registered with MCP decorators."""
        proto_content = '''
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
'''
        
        with TempProtoProject() as project:
            project.add_proto_file("tools.proto", proto_content)
            
            # Generate pb2 files  
            cmd_pb2 = [
                "python", "-m", "grpc_tools.protoc",
                f"--python_out={project.output_dir}",
                f"-I{project.proto_dir}",
                str(project.proto_dir / "tools.proto")
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
                'List': list,
                'Dict': dict,
                'Optional': type(None), 
                'Any': object,
                'FastMCP': mock_fastmcp,
                'json_format': MagicMock(),
            }
            
            # Execute the generated code
            locals_dict = assert_imports_successfully(mcp_code, mock_globals)
            
            # Call the server factory function
            server_factory = locals_dict['create_toolservice_server']
            server_factory()
            
            # Verify that the tool decorator was called for each RPC method
            # The decorator should be called twice (once for each tool)
            assert mock_fastmcp_instance.tool.call_count == 2
    
    def test_parameter_type_hints(self):
        """Test that generated functions have correct parameter type hints."""
        proto_content = '''
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
'''
        
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
            assert "tags: List[str]" in mcp_code
            assert "description: Optional[str] = None" in mcp_code
            assert "metadata: Dict[str, str]" in mcp_code
            
            # Check for proper imports
            assert "from typing import Optional, List, Dict, Any" in mcp_code
    
    def test_oneof_field_handling(self):
        """Test that oneof fields are properly handled in generated code."""
        proto_content = '''
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
'''
        
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
        proto_content = '''
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
'''
        
        with TempProtoProject() as project:
            project.add_proto_file("json.proto", proto_content)
            
            # Generate MCP files
            result = project.run_plugin(["json.proto"])
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Read and check the generated code
            mcp_code = project.read_generated_file("json_pb2_mcp.py")
            
            # Check for proper JSON serialization
            assert "json_format.MessageToDict" in mcp_code
            assert "use_integers_for_enums=True" in mcp_code
            assert "return result" in mcp_code
            
            # Check that response construction is present
            assert "response = json_pb2.JsonResponse()" in mcp_code
            assert "result = json_format.MessageToDict(response" in mcp_code