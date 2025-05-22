"""Protoc plugin for generating Python MCP server code."""

import sys
from typing import List, Optional, Dict, Any
from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf import descriptor_pb2


class McpPlugin:
    """
    Protoc plugin for generating Python MCP server code from Protocol Buffer service definitions.
    
    This plugin follows the standard protoc plugin protocol, reading a CodeGeneratorRequest
    from stdin and writing a CodeGeneratorResponse to stdout.
    """
    
    # Suffix for generated Python MCP files
    OUTPUT_FILE_SUFFIX = "_pb2_mcp.py"
    
    def __init__(self):
        """Initialize the MCP plugin."""
        self.parameters: Dict[str, str] = {}
        self.debug_mode: bool = False
        
    def log_debug(self, message: str) -> None:
        """Log debug message to stderr if debug mode is enabled."""
        if self.debug_mode:
            sys.stderr.write(f"[protoc-gen-py-mcp] {message}\n")
            sys.stderr.flush()
    
    def log_error(self, message: str) -> None:
        """Log error message to stderr."""
        sys.stderr.write(f"[protoc-gen-py-mcp ERROR] {message}\n")
        sys.stderr.flush()
    
    def parse_parameters(self, parameter_string: str) -> None:
        """
        Parse plugin parameters from the protoc parameter string.
        
        Parameters are in the format: key1=value1,key2=value2
        Special parameters:
        - debug: Enable debug logging
        """
        if not parameter_string:
            return
            
        for param in parameter_string.split(','):
            if '=' in param:
                key, value = param.split('=', 1)
                self.parameters[key.strip()] = value.strip()
            else:
                # Boolean flags
                self.parameters[param.strip()] = "true"
        
        # Handle special parameters
        self.debug_mode = self.parameters.get('debug', '').lower() in ('true', '1', 'yes')
        
        self.log_debug(f"Parsed parameters: {self.parameters}")
    
    def generate(self, request: plugin.CodeGeneratorRequest, response: plugin.CodeGeneratorResponse) -> None:
        """
        Generate MCP server code for all requested proto files.
        
        Args:
            request: The CodeGeneratorRequest from protoc
            response: The CodeGeneratorResponse to populate
        """
        try:
            # Parse plugin parameters
            self.parse_parameters(request.parameter)
            
            # Set supported features
            response.supported_features = plugin.CodeGeneratorResponse.Feature.FEATURE_PROTO3_OPTIONAL
            
            self.log_debug(f"Processing {len(request.file_to_generate)} files")
            
            # Only generate for explicitly requested files
            requested_files = set(request.file_to_generate)
            
            for proto_file in request.proto_file:
                if proto_file.name in requested_files:
                    self.log_debug(f"Generating MCP code for {proto_file.name}")
                    self.handle_file(proto_file, response)
                else:
                    self.log_debug(f"Skipping dependency file {proto_file.name}")
                    
        except Exception as e:
            error_msg = f"Plugin error: {str(e)}"
            self.log_error(error_msg)
            response.error = error_msg
    
    def handle_file(self, proto_file: descriptor_pb2.FileDescriptorProto, response: plugin.CodeGeneratorResponse) -> None:
        """
        Generate MCP server code for a single proto file.
        
        Args:
            proto_file: The FileDescriptorProto to process
            response: The CodeGeneratorResponse to add generated files to
        """
        try:
            # Validate file has services
            if not proto_file.service:
                self.log_debug(f"No services found in {proto_file.name}, skipping")
                return
            
            # Generate output filename
            output_filename = proto_file.name.replace(".proto", self.OUTPUT_FILE_SUFFIX)
            
            # Generate the content
            content = self.generate_file_content(proto_file)
            
            # Add to response
            generated_file = response.file.add()
            generated_file.name = output_filename
            generated_file.content = content
            
            self.log_debug(f"Generated {len(content)} characters for {output_filename}")
            
        except Exception as e:
            error_msg = f"Error processing file {proto_file.name}: {str(e)}"
            self.log_error(error_msg)
            response.error = error_msg
    
    def generate_file_content(self, proto_file: descriptor_pb2.FileDescriptorProto) -> str:
        """
        Generate the Python MCP server code content for a proto file.
        
        Args:
            proto_file: The FileDescriptorProto to generate code for
            
        Returns:
            The generated Python code as a string
        """
        lines = []
        
        # File header and imports
        self._generate_header(lines, proto_file)
        self._generate_imports(lines, proto_file)
        
        # Generate code for each service
        for service in proto_file.service:
            self._generate_service(lines, service, proto_file)
        
        return '\n'.join(lines) + '\n'
    
    def _generate_header(self, lines: List[str], proto_file: descriptor_pb2.FileDescriptorProto) -> None:
        """Generate file header comments."""
        lines.extend([
            f"# Generated from {proto_file.name}",
            "# DO NOT EDIT: This file is automatically generated by protoc-gen-py-mcp",
            f"# Plugin version: protoc-gen-py-mcp",
            "",
        ])
    
    def _generate_imports(self, lines: List[str], proto_file: descriptor_pb2.FileDescriptorProto) -> None:
        """Generate necessary imports for the generated code."""
        lines.extend([
            "from typing import Optional, List, Dict, Any",
            "from fastmcp import FastMCP",
            "from google.protobuf import json_format",
            "",
        ])
        
        # Import the corresponding pb2 module
        pb2_module = proto_file.name.replace(".proto", "_pb2").replace("/", ".")
        lines.append(f"import {pb2_module}")
        
        lines.append("")
    
    def _generate_service(self, lines: List[str], service: descriptor_pb2.ServiceDescriptorProto, 
                         proto_file: descriptor_pb2.FileDescriptorProto) -> None:
        """Generate MCP server factory function for a service."""
        service_name = service.name
        function_name = f"create_{service_name.lower()}_server"
        
        lines.extend([
            f"def {function_name}() -> FastMCP:",
            f'    """Create an MCP server for {service_name} service tools."""',
            f'    mcp = FastMCP("{service_name}")',
            "",
        ])
        
        # Generate tool functions for each method
        for method in service.method:
            self._generate_method_tool(lines, method, proto_file, indentation="    ")
        
        lines.extend([
            "    return mcp",
            "",
        ])
    
    def _generate_method_tool(self, lines: List[str], method: descriptor_pb2.MethodDescriptorProto,
                             proto_file: descriptor_pb2.FileDescriptorProto, indentation: str = "") -> None:
        """Generate an MCP tool function for a gRPC method."""
        method_name = method.name
        method_name_snake = self._camel_to_snake(method_name)
        
        lines.extend([
            f"{indentation}@mcp.tool()",
            f"{indentation}def {method_name_snake}() -> dict:",
            f'{indentation}    """Tool for {method_name} RPC method."""',
            f"{indentation}    # TODO: Implement {method_name} logic",
            f"{indentation}    # Input type: {method.input_type}",
            f"{indentation}    # Output type: {method.output_type}",
            f"{indentation}    ",
            f"{indentation}    # Placeholder response",
            f'{indentation}    return {{"status": "not_implemented", "method": "{method_name}"}}',
            f"{indentation}",
        ])
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append('_')
            result.append(char.lower())
        return ''.join(result)


def main() -> None:
    """
    Main entry point for the protoc-gen-py-mcp plugin.
    
    Reads a CodeGeneratorRequest from stdin, generates Python MCP server code,
    and writes a CodeGeneratorResponse to stdout.
    """
    try:
        # Read input from stdin
        data: bytes = sys.stdin.buffer.read()
        
        # Parse input as CodeGeneratorRequest
        request = plugin.CodeGeneratorRequest()
        request.ParseFromString(data)
        
        # Prepare response
        response = plugin.CodeGeneratorResponse()
        
        # Create plugin instance and generate code
        mcp_plugin = McpPlugin()
        mcp_plugin.generate(request, response)
        
        # Write response to stdout
        sys.stdout.buffer.write(response.SerializeToString())
        
    except Exception as e:
        # Last resort error handling
        sys.stderr.write(f"[protoc-gen-py-mcp FATAL] {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()