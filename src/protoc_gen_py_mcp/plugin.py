"""Protoc plugin for generating Python MCP server code."""

import sys
from typing import List, Optional, Dict, Any, Union
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
        
        # Type indexing for all proto files
        self.message_types: Dict[str, descriptor_pb2.DescriptorProto] = {}
        self.enum_types: Dict[str, descriptor_pb2.EnumDescriptorProto] = {}
        self.file_packages: Dict[str, str] = {}  # filename -> package name
        
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
    
    def _build_type_index(self, request: plugin.CodeGeneratorRequest) -> None:
        """
        Build a comprehensive index of all types from all proto files.
        
        This includes both the files we're generating for and their dependencies,
        so we can resolve any type references during code generation.
        """
        self.log_debug("Building type index from all proto files")
        
        for proto_file in request.proto_file:
            # Store package information
            self.file_packages[proto_file.name] = proto_file.package
            
            # Index message types
            self._index_messages(proto_file.message_type, proto_file.package)
            
            # Index enum types  
            self._index_enums(proto_file.enum_type, proto_file.package)
        
        self.log_debug(f"Indexed {len(self.message_types)} message types and {len(self.enum_types)} enum types")
    
    def _index_messages(self, messages: List[descriptor_pb2.DescriptorProto], package: str, 
                       parent_name: str = "") -> None:
        """
        Recursively index message types, including nested messages.
        
        Args:
            messages: List of message descriptors to index
            package: The package name for these messages
            parent_name: The parent message name for nested messages
        """
        for message in messages:
            # Build the fully qualified name
            if parent_name:
                full_name = f".{package}.{parent_name}.{message.name}"
            elif package:
                full_name = f".{package}.{message.name}"
            else:
                full_name = f".{message.name}"
            
            self.message_types[full_name] = message
            self.log_debug(f"Indexed message type: {full_name}")
            
            # Recursively index nested messages
            if message.nested_type:
                nested_parent = f"{parent_name}.{message.name}" if parent_name else message.name
                self._index_messages(message.nested_type, package, nested_parent)
            
            # Index nested enums
            if message.enum_type:
                nested_parent = f"{parent_name}.{message.name}" if parent_name else message.name
                self._index_enums(message.enum_type, package, nested_parent)
    
    def _index_enums(self, enums: List[descriptor_pb2.EnumDescriptorProto], package: str,
                    parent_name: str = "") -> None:
        """
        Index enum types.
        
        Args:
            enums: List of enum descriptors to index
            package: The package name for these enums
            parent_name: The parent message name for nested enums
        """
        for enum in enums:
            # Build the fully qualified name
            if parent_name:
                full_name = f".{package}.{parent_name}.{enum.name}"
            elif package:
                full_name = f".{package}.{enum.name}"
            else:
                full_name = f".{enum.name}"
            
            self.enum_types[full_name] = enum
            self.log_debug(f"Indexed enum type: {full_name}")
    
    def _get_python_type(self, field: descriptor_pb2.FieldDescriptorProto) -> str:
        """
        Map a proto field type to a Python type string for type hints.
        
        Args:
            field: The field descriptor to analyze
            
        Returns:
            Python type string (e.g., "str", "int", "List[str]", "Optional[int]")
        """
        # Handle repeated fields
        if field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED:
            element_type = self._get_scalar_python_type(field)
            return f"List[{element_type}]"
        
        # Handle optional fields
        # In proto3, fields are only truly optional if explicitly marked as proto3_optional
        # The label might be LABEL_OPTIONAL for all proto3 fields, but that doesn't mean they're optional in MCP terms
        is_optional = field.proto3_optional
        
        base_type = self._get_scalar_python_type(field)
        
        if is_optional:
            return f"Optional[{base_type}]"
        else:
            return base_type
    
    def _get_scalar_python_type(self, field: descriptor_pb2.FieldDescriptorProto) -> str:
        """
        Get the Python type for a scalar (non-repeated) field.
        
        Args:
            field: The field descriptor to analyze
            
        Returns:
            Python type string for the scalar type
        """
        type_mapping = {
            descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE: "float",
            descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT: "float", 
            descriptor_pb2.FieldDescriptorProto.TYPE_INT64: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_UINT64: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_INT32: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_BOOL: "bool",
            descriptor_pb2.FieldDescriptorProto.TYPE_STRING: "str",
            descriptor_pb2.FieldDescriptorProto.TYPE_BYTES: "bytes",
            descriptor_pb2.FieldDescriptorProto.TYPE_UINT32: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_SINT32: "int",
            descriptor_pb2.FieldDescriptorProto.TYPE_SINT64: "int",
        }
        
        if field.type in type_mapping:
            return type_mapping[field.type]
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
            # For enums, we'll use int (could be enhanced to use specific enum types)
            return "int"
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
            # For messages, we'll use dict (could be enhanced to use specific message types)
            return "dict"
        else:
            # Fallback for unknown types
            self.log_debug(f"Unknown field type {field.type} for field {field.name}, using Any")
            return "Any"
    
    def _analyze_message_fields(self, message_type_name: str) -> List[Dict[str, Any]]:
        """
        Analyze the fields of a message type to extract parameter information.
        
        Args:
            message_type_name: Fully qualified message type name (e.g., ".examples.v1.SetVibeRequest")
            
        Returns:
            List of field information dictionaries with keys:
            - name: field name
            - type: Python type string  
            - proto_type: Original proto field type
            - required: whether the field is required
            - repeated: whether the field is repeated
            - default_value: default value if any
        """
        if message_type_name not in self.message_types:
            self.log_debug(f"Message type {message_type_name} not found in type index")
            return []
        
        message = self.message_types[message_type_name]
        fields = []
        
        for field in message.field:
            # In proto3, fields are required by default unless explicitly marked as proto3_optional
            # The LABEL_OPTIONAL might be set for all proto3 fields, but only proto3_optional matters
            is_optional = field.proto3_optional
            is_repeated = field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
            is_required = not is_optional and not is_repeated
            
            field_info = {
                'name': field.name,
                'type': self._get_python_type(field),
                'proto_type': field.type,
                'required': is_required,
                'repeated': is_repeated,
                'optional': is_optional,
                'type_name': field.type_name if field.type_name else None
            }
            
            fields.append(field_info)
            self.log_debug(f"Analyzed field {field.name}: {field_info['type']}")
        
        return fields
    
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
            
            # Build comprehensive type index from all proto files
            self._build_type_index(request)
            
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
        
        # Analyze input message fields to generate function parameters
        input_fields = self._analyze_message_fields(method.input_type)
        
        # Generate function signature with parameters
        params = []
        for field in input_fields:
            if field['optional']:
                params.append(f"{field['name']}: {field['type']} = None")
            else:
                params.append(f"{field['name']}: {field['type']}")
        
        param_str = ", ".join(params)
        
        lines.extend([
            f"{indentation}@mcp.tool()",
            f"{indentation}def {method_name_snake}({param_str}) -> dict:",
            f'{indentation}    """Tool for {method_name} RPC method."""',
        ])
        
        # Generate parameter documentation if we have input fields
        if input_fields:
            lines.append(f"{indentation}    # Parameters:")
            for field in input_fields:
                lines.append(f"{indentation}    #   {field['name']}: {field['type']}")
            lines.append(f"{indentation}    ")
        
        # Generate request message construction
        pb2_module = proto_file.name.replace(".proto", "_pb2").replace("/", ".")
        input_type_name = method.input_type.split('.')[-1]  # Get the simple name
        
        lines.extend([
            f"{indentation}    # Construct request message",
            f"{indentation}    request = {pb2_module}.{input_type_name}()",
        ])
        
        # Generate field assignment code
        for field in input_fields:
            if field['optional']:
                lines.extend([
                    f"{indentation}    if {field['name']} is not None:",
                    f"{indentation}        request.{field['name']} = {field['name']}",
                ])
            else:
                lines.append(f"{indentation}    request.{field['name']} = {field['name']}")
        
        # Generate response handling
        output_type_name = method.output_type.split('.')[-1]  # Get the simple name
        
        lines.extend([
            f"{indentation}    ",
            f"{indentation}    # TODO: Implement actual {method_name} logic here",
            f"{indentation}    # For now, create an empty response",
            f"{indentation}    response = {pb2_module}.{output_type_name}()",
            f"{indentation}    ",
            f"{indentation}    # Convert response to dict for MCP",
            f"{indentation}    result = json_format.MessageToDict(response, use_integers_for_enums=True)",
            f"{indentation}    return result",
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