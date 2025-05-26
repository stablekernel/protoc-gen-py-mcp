"""Protoc plugin for generating Python MCP server code."""

import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, TypedDict

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2 as plugin

from .core.config import CodeGenerationOptions, ConfigManager, PluginConfig
from .core.type_analyzer import TypeAnalyzer
from .core.utils import ErrorUtils, NamingUtils


class FieldInfo(TypedDict, total=False):
    """Type definition for field information dictionaries."""

    name: str
    type: str
    proto_type: str
    optional: bool
    repeated: bool
    is_oneof: bool
    oneof_name: str


@dataclass
class MethodGenerationContext:
    """Context information for generating a single method tool."""

    method: descriptor_pb2.MethodDescriptorProto
    service: descriptor_pb2.ServiceDescriptorProto
    proto_file: descriptor_pb2.FileDescriptorProto
    service_index: int
    method_index: int
    indentation: str = ""


class McpPlugin:
    """
    Protoc plugin for generating Python MCP server code from Protocol Buffer service definitions.

    This plugin follows the standard protoc plugin protocol, reading a CodeGeneratorRequest
    from stdin and writing a CodeGeneratorResponse to stdout.
    """

    # Default suffix for generated Python MCP files (can be overridden by parameters)
    DEFAULT_OUTPUT_FILE_SUFFIX = "_pb2_mcp.py"
    # Keep for backward compatibility with tests
    OUTPUT_FILE_SUFFIX = "_pb2_mcp.py"

    def __init__(self) -> None:
        """Initialize the MCP plugin."""
        self.config_manager = ConfigManager()
        self.config: PluginConfig = PluginConfig()

        # Set compatibility attributes
        self.debug_mode = self.config.debug_mode
        self.debug_level = self.config.debug_level

        # Type indexing for all proto files
        self.message_types: Dict[str, descriptor_pb2.DescriptorProto] = {}
        self.enum_types: Dict[str, descriptor_pb2.EnumDescriptorProto] = {}
        self.file_packages: Dict[str, str] = {}  # filename -> package name

        # Comment extraction
        self.source_comments: Dict[str, Dict[tuple, str]] = {}  # filename -> path -> comment

        # Type analyzer (initialized after type indexing)
        self.type_analyzer: Optional[TypeAnalyzer] = None

    def log_debug(self, message: str, level: str = "basic") -> None:
        """Log debug message to stderr if debug mode is enabled."""
        if self.config.debug_mode and self.config_manager.should_log_level(level):
            sys.stderr.write(f"[protoc-gen-py-mcp] {message}\n")
            sys.stderr.flush()

    def log_verbose(self, message: str) -> None:
        """Log verbose debug message."""
        self.log_debug(message, "verbose")

    def log_trace(self, message: str) -> None:
        """Log trace debug message."""
        self.log_debug(message, "trace")

    def log_error(self, message: str) -> None:
        """Log error message to stderr."""
        sys.stderr.write(f"[protoc-gen-py-mcp ERROR] {message}\n")
        sys.stderr.flush()

    def log_warning(self, message: str) -> None:
        """Log warning message to stderr."""
        sys.stderr.write(f"[protoc-gen-py-mcp WARNING] {message}\n")
        sys.stderr.flush()

    def _has_optional_fields(self, proto_file: descriptor_pb2.FileDescriptorProto) -> bool:
        """Check if proto file has any optional fields that would need Optional typing."""
        if self.type_analyzer:
            return self.type_analyzer.has_optional_fields(proto_file)
        return False

    def parse_parameters(self, parameter_string: str) -> None:
        """Parse plugin parameters using the configuration manager."""
        self.config = self.config_manager.parse_parameters(parameter_string or "")
        self.debug_mode = self.config.debug_mode
        self.debug_level = self.config.debug_level

        self.log_debug(f"Parsed configuration: {self.config}")
        self.log_debug(f"Debug level: {self.debug_level}")

    def _create_detailed_error_context(self, file_name: str, exception: Exception) -> str:
        """Create detailed error message with context and troubleshooting tips."""
        return ErrorUtils.create_detailed_error_context(file_name, exception, self.debug_mode)

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

            # Extract comments from source code info
            self._extract_comments(proto_file)

            # Index message types
            self._index_messages(proto_file.message_type, proto_file.package)

            # Index enum types
            self._index_enums(proto_file.enum_type, proto_file.package)

            if self.config.show_type_details:
                self.log_verbose(
                    f"File {proto_file.name}: {len(proto_file.message_type)} messages, {len(proto_file.enum_type)} enums"
                )

        self.log_debug(
            f"Indexed {len(self.message_types)} message types and {len(self.enum_types)} enum types"
        )

        # Initialize type analyzer with indexed types
        self.type_analyzer = TypeAnalyzer(self.message_types, self.enum_types, self)

    def _extract_comments(self, proto_file: descriptor_pb2.FileDescriptorProto) -> None:
        """
        Extract comments from proto file source code info.

        Args:
            proto_file: The proto file descriptor to extract comments from
        """
        if not proto_file.source_code_info:
            return

        comments = {}
        for location in proto_file.source_code_info.location:
            # Convert path list to tuple for use as dict key
            path_key = tuple(location.path)

            # Combine leading and trailing comments
            comment_parts = []
            if location.leading_comments:
                comment_parts.append(location.leading_comments.strip())
            if location.trailing_comments:
                comment_parts.append(location.trailing_comments.strip())

            if comment_parts:
                comments[path_key] = " ".join(comment_parts)

        self.source_comments[proto_file.name] = comments
        self.log_debug(f"Extracted {len(comments)} comments from {proto_file.name}")

    def _get_comment(self, proto_file_name: str, path: Sequence[int]) -> str:
        """
        Get comment for a specific path in a proto file.

        Args:
            proto_file_name: Name of the proto file
            path: Path to the element (e.g., service, method, message field)

        Returns:
            Comment string if found, empty string otherwise
        """
        if proto_file_name not in self.source_comments:
            return ""

        path_key = tuple(path)
        return self.source_comments[proto_file_name].get(path_key, "")

    def _index_messages(
        self,
        messages: Sequence[descriptor_pb2.DescriptorProto],
        package: str,
        parent_name: str = "",
    ) -> None:
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

    def _index_enums(
        self,
        enums: Sequence[descriptor_pb2.EnumDescriptorProto],
        package: str,
        parent_name: str = "",
    ) -> None:
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

    def generate(
        self, request: plugin.CodeGeneratorRequest, response: plugin.CodeGeneratorResponse
    ) -> None:
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
            response.supported_features = (
                plugin.CodeGeneratorResponse.Feature.FEATURE_PROTO3_OPTIONAL
            )

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

    def handle_file(
        self, proto_file: descriptor_pb2.FileDescriptorProto, response: plugin.CodeGeneratorResponse
    ) -> None:
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
            output_filename = proto_file.name.replace(".proto", self.config.output_suffix)

            # Generate the content
            content = self.generate_file_content(proto_file)

            # Add to response
            generated_file = response.file.add()
            generated_file.name = output_filename
            generated_file.content = content

            self.log_debug(f"Generated {len(content)} characters for {output_filename}")

            if self.config.show_generated_code:
                self.log_verbose(f"Generated content for {output_filename}:")
                for i, line in enumerate(content.split("\n"), 1):
                    self.log_trace(f"  {i:3d}: {line}")

        except Exception as e:
            # Create detailed error message with context
            error_context = self._create_detailed_error_context(proto_file.name, e)
            self.log_error(error_context)
            response.error = error_context

    def generate_file_content(self, proto_file: descriptor_pb2.FileDescriptorProto) -> str:
        """
        Generate the Python MCP server code content for a proto file.

        Args:
            proto_file: The FileDescriptorProto to generate code for

        Returns:
            The generated Python code as a string
        """
        lines: List[str] = []

        # File header and imports
        self._generate_header(lines, proto_file)
        self._generate_imports(lines, proto_file)

        # Generate code for each service
        service_names = []
        for service in proto_file.service:
            self._generate_service(lines, service, proto_file)
            service_names.append(service.name)

        # Generate main execution block
        self._generate_main_block(lines, service_names)

        return "\n".join(lines) + "\n"

    def _generate_header(
        self, lines: List[str], proto_file: descriptor_pb2.FileDescriptorProto
    ) -> None:
        """Generate file header comments."""
        lines.extend(
            [
                f"# Generated from {proto_file.name}",
                "# DO NOT EDIT: This file is automatically generated by protoc-gen-py-mcp",
                "# Plugin version: protoc-gen-py-mcp",
                "",
            ]
        )

    def _generate_imports(
        self, lines: List[str], proto_file: descriptor_pb2.FileDescriptorProto
    ) -> None:
        """Generate necessary imports for the generated code."""
        # Basic imports
        if self.config.async_mode:
            lines.append("import asyncio")

        # Import typing only what's needed
        typing_imports = (
            ["from typing import Optional"] if self._has_optional_fields(proto_file) else []
        )

        if typing_imports:
            lines.extend(typing_imports)

        lines.extend(
            [
                "from fastmcp import FastMCP",
            ]
        )

        lines.append("import grpc")  # Always include gRPC imports

        lines.append("")

        # Import the corresponding pb2 module
        pb2_module = proto_file.name.replace(".proto", "_pb2").replace("/", ".")
        lines.append(f"import {pb2_module}")

        # Always import gRPC stub
        grpc_module = proto_file.name.replace(".proto", "_pb2_grpc").replace("/", ".")
        lines.append(f"import {grpc_module}")

        lines.append("")

        # Generate default request interceptor if interceptor pattern is enabled
        if self.config.use_request_interceptor:
            lines.extend(
                [
                    "# Default request interceptor function",
                    "def default_request_interceptor(request, method_name, metadata):",
                    '    """Default request interceptor - no modifications."""',
                    "    return request, metadata",
                    "",
                    "# Global request interceptor - can be overridden by user",
                    "request_interceptor = default_request_interceptor",
                    "",
                ]
            )

    def _generate_main_block(self, lines: List[str], service_names: List[str]) -> None:
        """Generate main execution block like the target file."""
        lines.extend(
            [
                "",
                "",
                "if __name__ == '__main__':",
                "    mcp.run()",
            ]
        )

    def _generate_service(
        self,
        lines: List[str],
        service: descriptor_pb2.ServiceDescriptorProto,
        proto_file: descriptor_pb2.FileDescriptorProto,
    ) -> None:
        """Generate MCP server code."""
        self._generate_service_impl(lines, service, proto_file)

    def _generate_service_impl(
        self,
        lines: List[str],
        service: descriptor_pb2.ServiceDescriptorProto,
        proto_file: descriptor_pb2.FileDescriptorProto,
    ) -> None:
        """Generate global MCP server instance like the target file."""
        # Try to get service comment from source code info
        service_index = list(proto_file.service).index(service)

        # Create global MCP instance like the target file
        if service_index == 0:  # Only create one global instance for the first service
            lines.extend(
                [
                    'mcp = FastMCP("MCP Server from Proto")',
                    "",
                ]
            )

        # Generate tool functions for each method at global level
        for method_index, method in enumerate(service.method):
            # Add proper spacing between functions (2 blank lines for module-level functions)
            if method_index > 0:
                lines.append("")  # Add extra blank line between functions for PEP8
            lines.append("")  # Always add blank line before function decorator

            # Check if this is a streaming method
            is_client_stream = method.client_streaming
            is_server_stream = method.server_streaming

            if is_client_stream or is_server_stream:
                self._handle_streaming_method(
                    lines, method, service, proto_file, service_index, method_index
                )
            else:
                context = MethodGenerationContext(
                    method=method,
                    service=service,
                    proto_file=proto_file,
                    service_index=service_index,
                    method_index=method_index,
                    indentation="",
                )
                options = self.config_manager.create_code_generation_options()
                self._generate_method_tool(lines, context, options)

    def _generate_method_tool(
        self,
        lines: List[str],
        context: MethodGenerationContext,
        options: CodeGenerationOptions,
    ) -> None:
        """Generate an MCP tool function for a gRPC method."""
        method_name = context.method.name
        method_name_converted = self._convert_tool_name(method_name, options.tool_name_case)

        # Analyze input message fields to generate function parameters
        input_fields = (
            self.type_analyzer.analyze_message_fields(context.method.input_type)
            if self.type_analyzer
            else []
        )

        # Generate function signature with parameters
        # Separate required and optional parameters to ensure proper Python syntax
        required_params = []
        optional_params = []

        for field in input_fields:
            if field["optional"]:
                optional_params.append(f"{field['name']}: {field['type']} = None")
            else:
                required_params.append(f"{field['name']}: {field['type']}")

        # Required parameters must come before optional parameters in Python
        params = required_params + optional_params
        param_str = ", ".join(params)

        # Try to get method comment from source code info
        # Method path is [6, service_index, 2, method_index] where:
        # 6 = services field, 2 = methods field within service
        method_comment = self._get_comment(
            context.proto_file.name, [6, context.service_index, 2, context.method_index]
        )

        # Create enhanced docstring with method comment if available (if comments are enabled)
        if options.include_comments and method_comment:
            # Clean up the comment to avoid trailing whitespace
            clean_comment = method_comment.strip()
            docstring = f'{context.indentation}    """Tool for {method_name} RPC method.\n{context.indentation}\n{context.indentation}    {clean_comment}\n{context.indentation}    """'
        else:
            docstring = f'{context.indentation}    """Tool for {method_name} RPC method."""'

        # Generate function definition with explicit tool name and description
        if method_comment:
            # Use the actual proto comment, clean it up for single line
            tool_description = method_comment.replace("\n", " ").strip()
        else:
            # Fallback to generic description
            tool_description = f"Generated tool for {method_name} RPC method"

        if options.async_mode:
            lines.extend(
                [
                    f'{context.indentation}@mcp.tool(name="{method_name}", description="{tool_description}")',
                    f"{context.indentation}async def {method_name_converted}({param_str}):",
                    docstring,
                ]
            )
        else:
            lines.extend(
                [
                    f'{context.indentation}@mcp.tool(name="{method_name}", description="{tool_description}")',
                    f"{context.indentation}def {method_name_converted}({param_str}):",
                    docstring,
                ]
            )

        # Generate request message construction
        pb2_module = context.proto_file.name.replace(".proto", "_pb2").replace("/", ".")
        input_type_name = context.method.input_type.split(".")[-1]  # Get the simple name

        lines.extend(
            [
                f"{context.indentation}    # Construct request message",
                f"{context.indentation}    request = {pb2_module}.{input_type_name}()",
            ]
        )

        # Generate oneof validation if needed
        oneofs: Dict[str, List[str]] = {}
        for field in input_fields:
            if field.get("is_oneof", False):
                oneof_name = field["oneof_name"]
                if oneof_name not in oneofs:
                    oneofs[oneof_name] = []
                oneofs[oneof_name].append(field["name"])

        # Add oneof validation comments
        if oneofs:
            lines.append(f"{context.indentation}    # Oneof validation:")
            for oneof_name, field_names in oneofs.items():
                field_list = ", ".join(field_names)
                lines.append(
                    f"{context.indentation}    # Only one of [{field_list}] should be provided for oneof '{oneof_name}'"
                )

        # Generate field assignment code
        for field in input_fields:
            if field["optional"]:
                lines.extend(
                    [
                        f"{context.indentation}    if {field['name']} is not None:",
                        f"{context.indentation}        request.{field['name']} = {field['name']}",
                    ]
                )
            else:
                lines.append(f"{context.indentation}    request.{field['name']} = {field['name']}")

        # Add spacing before gRPC call
        if input_fields:  # Only add space if there were fields assigned
            lines.append("")

        # Generate functional gRPC call
        self._generate_grpc_call(lines, context, options)

    def _generate_grpc_call(
        self,
        lines: List[str],
        context: MethodGenerationContext,
        options: CodeGenerationOptions,
    ) -> None:
        """Generate actual gRPC call implementation."""
        method_name = context.method.name
        grpc_module = context.proto_file.name.replace(".proto", "_pb2_grpc").replace("/", ".")

        # Get service name from context
        service_name = context.service.name

        grpc_target = (
            options.grpc_target or "localhost:50051"
        )  # Default target like the target file

        # Generate gRPC call with request interceptor pattern
        if options.use_request_interceptor:
            lines.extend(
                [
                    f"{context.indentation}    # Apply request interceptor for auth/logging/modifications",
                    f"{context.indentation}    request, metadata = request_interceptor(request, '{method_name}', ())",
                    "",
                    f"{context.indentation}    channel = grpc.insecure_channel('{grpc_target}')",
                    f"{context.indentation}    stub = {grpc_module}.{service_name}Stub(channel)",
                    f"{context.indentation}    response = stub.{method_name}(request, metadata=metadata)",
                ]
            )
        else:
            lines.extend(
                [
                    f"{context.indentation}    channel = grpc.insecure_channel('{grpc_target}')",
                    f"{context.indentation}    stub = {grpc_module}.{service_name}Stub(channel)",
                    f"{context.indentation}    response = stub.{method_name}(request)",
                ]
            )

        lines.extend(
            [
                "",
                f"{context.indentation}    # Convert protobuf response to dict for MCP",
                f"{context.indentation}    from google.protobuf.json_format import MessageToDict",
                f"{context.indentation}    result = MessageToDict(response)",
                f"{context.indentation}    return result",
            ]
        )

    def _handle_streaming_method(
        self,
        lines: List[str],
        method: descriptor_pb2.MethodDescriptorProto,
        service: descriptor_pb2.ServiceDescriptorProto,
        proto_file: descriptor_pb2.FileDescriptorProto,
        service_index: int,
        method_index: int,
    ) -> None:
        """Handle streaming RPC methods based on stream_mode setting."""
        stream_mode = self.config.stream_mode
        method_name = method.name
        is_client_stream = method.client_streaming
        is_server_stream = method.server_streaming

        if stream_mode == "skip":
            # Skip streaming methods entirely
            self.log_debug(
                f"Skipping streaming method {method_name} (client_stream={is_client_stream}, server_stream={is_server_stream})"
            )
            lines.extend(
                [
                    f"    # Skipped streaming method: {method_name}",
                    f"    # Client streaming: {is_client_stream}, Server streaming: {is_server_stream}",
                    "",
                ]
            )
            return

        if stream_mode == "warn":
            # Generate with warning comments
            lines.extend(
                [
                    f"    # WARNING: {method_name} is a streaming RPC",
                    f"    # Client streaming: {is_client_stream}, Server streaming: {is_server_stream}",
                    "    # Streaming RPCs may not work well with MCP's request/response model",
                    "",
                ]
            )

        if is_client_stream and is_server_stream:
            # Bidirectional streaming - not easily adaptable to MCP
            if stream_mode == "collect":
                lines.extend(
                    [
                        f"    # NOTE: {method_name} is bidirectional streaming - not supported",
                        "    # Consider using separate unary RPCs for MCP integration",
                        "",
                    ]
                )
                return
            else:
                self.log_debug(
                    f"Warning: Bidirectional streaming method {method_name} may not work properly with MCP"
                )

        # For server/client streaming, generate adapted version
        if stream_mode == "collect":
            self._generate_streaming_tool_adapted(
                lines, method, proto_file, service_index, method_index
            )
        else:
            # Generate normal tool but with streaming handling
            context = MethodGenerationContext(
                method=method,
                service=service,
                proto_file=proto_file,
                service_index=service_index,
                method_index=method_index,
                indentation="    ",
            )
            options = self.config_manager.create_code_generation_options()
            self._generate_method_tool(lines, context, options)

    def _generate_streaming_tool_adapted(
        self,
        lines: List[str],
        method: descriptor_pb2.MethodDescriptorProto,
        proto_file: descriptor_pb2.FileDescriptorProto,
        service_index: int,
        method_index: int,
    ) -> None:
        """Generate adapted tool for streaming RPC that collects all responses."""
        method_name = method.name
        method_name_converted = self._convert_tool_name(method_name)
        is_client_stream = method.client_streaming
        is_server_stream = method.server_streaming

        if is_client_stream and is_server_stream:
            # Bidirectional - skip
            return

        # Analyze input message fields
        input_fields = (
            self.type_analyzer.analyze_message_fields(method.input_type)
            if self.type_analyzer
            else []
        )

        # For client streaming, we'll accept a list of requests
        if is_client_stream:
            # Modify to accept list of inputs
            params = ["requests: List[dict]"]
        else:
            # Regular unary input
            required_params = []
            optional_params = []

            for field in input_fields:
                if field["optional"]:
                    optional_params.append(f"{field['name']}: {field['type']} = None")
                else:
                    required_params.append(f"{field['name']}: {field['type']}")

            params = required_params + optional_params

        param_str = ", ".join(params)

        # Get comment
        method_comment = self._get_comment(proto_file.name, [6, service_index, 2, method_index])

        # Enhanced docstring for streaming
        stream_type = "client streaming" if is_client_stream else "server streaming"
        if self.config.include_comments and method_comment:
            docstring = f'    """Tool for {method_name} RPC method ({stream_type}).\n    \n    {method_comment}\n    \n    Note: This is a {stream_type} RPC adapted for MCP.\n    """'
        else:
            docstring = f'    """Tool for {method_name} RPC method ({stream_type})."""'

        # Generate function
        if self.config.async_mode:
            lines.extend(
                [
                    "    @mcp.tool()",
                    f"    async def {method_name_converted}({param_str}) -> dict:",
                    docstring,
                ]
            )
        else:
            lines.extend(
                [
                    "    @mcp.tool()",
                    f"    def {method_name_converted}({param_str}) -> dict:",
                    docstring,
                ]
            )

        # Generate implementation comment
        lines.extend(
            [
                f"        # NOTE: This is a {stream_type} RPC adapted for MCP",
                "        # Results are collected and returned as a list",
                "",
            ]
        )

        # Add TODO implementation for now
        if is_client_stream:
            lines.extend(
                [
                    "        # TODO: Implement client streaming logic",
                    "        # Process list of requests and send them to the streaming RPC",
                    "        # Return collected responses",
                    "        return {'error': 'Client streaming not yet implemented'}",
                ]
            )
        else:
            lines.extend(
                [
                    "        # TODO: Implement server streaming logic",
                    "        # Send single request and collect all streaming responses",
                    "        # Return list of responses",
                    "        return {'error': 'Server streaming not yet implemented'}",
                ]
            )

        lines.append("")

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        return NamingUtils.camel_to_snake(name)

    def _convert_tool_name(self, method_name: str, case_type: Optional[str] = None) -> str:
        """Convert method name according to tool_name_case setting."""
        if case_type is None:
            case_type = self.config.tool_name_case
        return NamingUtils.convert_tool_name(method_name, case_type)


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
        # Enhanced last resort error handling
        import traceback

        error_msg_parts = [
            "[protoc-gen-py-mcp FATAL] Plugin execution failed",
            f"Error: {type(e).__name__}: {str(e)}",
            "",
            "This is likely due to one of the following:",
            "1. Invalid protobuf input (malformed .proto file)",
            "2. Missing dependencies or corrupted installation",
            "3. Unsupported protobuf features",
            "4. System-level issues (permissions, disk space, etc.)",
            "",
            "Troubleshooting steps:",
            "1. Verify your .proto file syntax: protoc --decode_raw < your_file.proto",
            "2. Reinstall the plugin: pip install --force-reinstall protoc-gen-py-mcp",
            "3. Check protoc version: protoc --version (requires 3.20+)",
            '4. Enable debug mode: --py-mcp_opt="debug=trace"',
            "5. Report issue at: https://github.com/your-org/protoc-gen-py-mcp/issues",
            "",
            f"Stack trace:\n{traceback.format_exc()}",
        ]

        sys.stderr.write("\n".join(error_msg_parts))
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
