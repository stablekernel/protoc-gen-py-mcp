"""End-to-end integration tests for the protoc plugin."""

import pytest
from pathlib import Path
import tempfile
import subprocess
import sys

from tests.test_utils import TempProtoProject, assert_valid_python_code, assert_imports_successfully


class TestEndToEndGeneration:
    """Test end-to-end code generation functionality."""
    
    def test_simple_service_generation(self):
        """Test generating code for a simple service."""
        proto_content = '''
syntax = "proto3";

package test.simple;

message SimpleRequest {
  string name = 1;
  int32 value = 2;
}

message SimpleResponse {
  string result = 1;
  bool success = 2;
}

service SimpleService {
  rpc DoSomething(SimpleRequest) returns (SimpleResponse) {}
}
'''
        
        with TempProtoProject() as project:
            # Add the proto file
            project.add_proto_file("simple.proto", proto_content)
            
            # Run the plugin
            result = project.run_plugin(["simple.proto"])
            
            # Check that the command succeeded
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Check that the output file was generated
            output_file = project.get_generated_file("simple_pb2_mcp.py")
            assert output_file.exists(), "Generated file does not exist"
            
            # Read and validate the generated code
            generated_code = project.read_generated_file("simple_pb2_mcp.py")
            
            # Basic content checks
            assert "def create_simpleservice_server()" in generated_code
            assert "FastMCP" in generated_code
            assert "def do_something(" in generated_code
            assert "name: str" in generated_code
            assert "value: int" in generated_code
            
            # Validate that it's syntactically correct Python
            assert_valid_python_code(generated_code)
    
    def test_complex_features_generation(self):
        """Test generating code for advanced proto features."""
        proto_content = '''
syntax = "proto3";

package test.complex;

enum Priority {
  PRIORITY_UNSPECIFIED = 0;
  PRIORITY_LOW = 1;
  PRIORITY_HIGH = 2;
}

message NestedMessage {
  string text = 1;
  int64 timestamp = 2;
}

message ComplexRequest {
  string name = 1;
  optional string description = 2;
  repeated string tags = 3;
  Priority priority = 4;
  NestedMessage metadata = 5;
  map<string, string> attributes = 6;
  
  oneof action {
    string create = 7;
    string update = 8;
    bool delete = 9;
  }
}

message ComplexResponse {
  bool success = 1;
  repeated string errors = 2;
}

service ComplexService {
  rpc ProcessComplex(ComplexRequest) returns (ComplexResponse) {}
}
'''
        
        with TempProtoProject() as project:
            # Add the proto file
            project.add_proto_file("complex.proto", proto_content)
            
            # Run the plugin
            result = project.run_plugin(["complex.proto"])
            
            # Check that the command succeeded
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Check that the output file was generated
            output_file = project.get_generated_file("complex_pb2_mcp.py")
            assert output_file.exists(), "Generated file does not exist"
            
            # Read and validate the generated code
            generated_code = project.read_generated_file("complex_pb2_mcp.py")
            
            # Check for advanced features
            assert "Optional[str]" in generated_code  # Optional fields
            assert "List[str]" in generated_code     # Repeated fields
            assert "Dict[str, str]" in generated_code # Map fields
            assert "priority: int" in generated_code  # Enum fields
            assert "metadata: dict" in generated_code # Nested messages
            
            # Check for oneof handling
            assert "# Oneof validation:" in generated_code
            assert "create: Optional[str] = None" in generated_code
            assert "update: Optional[str] = None" in generated_code
            assert "delete: Optional[bool] = None" in generated_code
            
            # Validate that it's syntactically correct Python
            assert_valid_python_code(generated_code)
    
    def test_well_known_types_generation(self):
        """Test generating code for well-known types."""
        proto_content = '''
syntax = "proto3";

package test.wellknown;

import "google/protobuf/timestamp.proto";
import "google/protobuf/duration.proto";
import "google/protobuf/struct.proto";
import "google/protobuf/wrappers.proto";

message WellKnownRequest {
  google.protobuf.Timestamp created_at = 1;
  google.protobuf.Duration timeout = 2;
  google.protobuf.Struct config = 3;
  google.protobuf.StringValue title = 4;
  google.protobuf.Int32Value count = 5;
}

message WellKnownResponse {
  google.protobuf.Timestamp processed_at = 1;
  bool success = 2;
}

service WellKnownService {
  rpc ProcessWellKnown(WellKnownRequest) returns (WellKnownResponse) {}
}
'''
        
        with TempProtoProject() as project:
            # Add the proto file
            project.add_proto_file("wellknown.proto", proto_content)
            
            # Run the plugin  
            result = project.run_plugin(["wellknown.proto"])
            
            # Check that the command succeeded
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Check that the output file was generated
            output_file = project.get_generated_file("wellknown_pb2_mcp.py")
            assert output_file.exists(), "Generated file does not exist"
            
            # Read and validate the generated code
            generated_code = project.read_generated_file("wellknown_pb2_mcp.py")
            
            # Check for well-known type mappings
            assert "created_at: str" in generated_code    # Timestamp -> str
            assert "timeout: str" in generated_code       # Duration -> str  
            assert "config: dict" in generated_code       # Struct -> dict
            assert "title: str" in generated_code         # StringValue -> str
            assert "count: int" in generated_code         # Int32Value -> int
            
            # Validate that it's syntactically correct Python
            assert_valid_python_code(generated_code)
    
    def test_multiple_services_generation(self):
        """Test generating code for multiple services in one file."""
        proto_content = '''
syntax = "proto3";

package test.multi;

message Request1 {
  string data = 1;
}

message Response1 {
  string result = 1;
}

message Request2 {
  int32 number = 1;
}

message Response2 {
  bool success = 1;
}

service Service1 {
  rpc Method1(Request1) returns (Response1) {}
}

service Service2 {
  rpc Method2(Request2) returns (Response2) {}
}
'''
        
        with TempProtoProject() as project:
            # Add the proto file
            project.add_proto_file("multi.proto", proto_content)
            
            # Run the plugin
            result = project.run_plugin(["multi.proto"])
            
            # Check that the command succeeded
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Check that the output file was generated
            output_file = project.get_generated_file("multi_pb2_mcp.py")
            assert output_file.exists(), "Generated file does not exist"
            
            # Read and validate the generated code
            generated_code = project.read_generated_file("multi_pb2_mcp.py")
            
            # Check for both services
            assert "def create_service1_server()" in generated_code
            assert "def create_service2_server()" in generated_code
            assert "def method1(" in generated_code
            assert "def method2(" in generated_code
            
            # Validate that it's syntactically correct Python
            assert_valid_python_code(generated_code)
    
    def test_empty_service_handling(self):
        """Test handling of proto files with no services."""
        proto_content = '''
syntax = "proto3";

package test.empty;

message OnlyMessage {
  string data = 1;
}
'''
        
        with TempProtoProject() as project:
            # Add the proto file
            project.add_proto_file("empty.proto", proto_content)
            
            # Run the plugin
            result = project.run_plugin(["empty.proto"])
            
            # The plugin should succeed but not generate any files
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Check that no output file was generated (since no services)
            output_file = project.get_generated_file("empty_pb2_mcp.py")
            assert not output_file.exists(), "No file should be generated for proto without services"
    
    def test_plugin_debug_mode(self):
        """Test that debug mode works and produces debug output."""
        proto_content = '''
syntax = "proto3";

package test.debug;

message DebugRequest {
  string name = 1;
}

message DebugResponse {
  string result = 1;
}

service DebugService {
  rpc Debug(DebugRequest) returns (DebugResponse) {}
}
'''
        
        with TempProtoProject() as project:
            # Add the proto file
            project.add_proto_file("debug.proto", proto_content)
            
            # Run protoc with debug parameter
            cmd = [
                "python", "-m", "grpc_tools.protoc",
                f"--py-mcp_out={project.output_dir}",
                f"--py-mcp_opt=debug=true",
                f"-I{project.proto_dir}",
                str(project.proto_dir / "debug.proto")
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project.temp_dir
            )
            
            # Check that the command succeeded
            assert result.returncode == 0, f"Plugin failed: {result.stderr}"
            
            # Check that debug output was produced
            assert "[protoc-gen-py-mcp]" in result.stderr
            
            # Check that the output file was generated
            output_file = project.get_generated_file("debug_pb2_mcp.py")
            assert output_file.exists(), "Generated file does not exist"