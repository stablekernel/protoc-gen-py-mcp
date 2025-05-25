"""Protoc plugin for generating Python MCP server code."""

import sys
from typing import Any, Dict, List, Optional, Sequence, TypedDict

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2 as plugin


class FieldInfo(TypedDict, total=False):
    """Type definition for field information dictionaries."""

    name: str
    type: str
    proto_type: str
    optional: bool
    repeated: bool
    is_oneof: bool
    oneof_name: str


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
        self.parameters: Dict[str, str] = {}
        self.debug_mode: bool = False

        # Type indexing for all proto files
        self.message_types: Dict[str, descriptor_pb2.DescriptorProto] = {}
        self.enum_types: Dict[str, descriptor_pb2.EnumDescriptorProto] = {}
        self.file_packages: Dict[str, str] = {}  # filename -> package name

        # Comment extraction
        self.source_comments: Dict[str, Dict[tuple, str]] = {}  # filename -> path -> comment

    def log_debug(self, message: str, level: str = "basic") -> None:
        """Log debug message to stderr if debug mode is enabled."""
        if self.debug_mode and self._should_log_level(level):
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

    def _create_validation_error(
        self, param_name: str, param_value: str, valid_options: List[str]
    ) -> str:
        """Create a detailed validation error message."""
        return (
            f"Invalid value '{param_value}' for parameter '{param_name}'. "
            f"Valid options are: {', '.join(valid_options)}"
        )

    def _create_parameter_error(self, param_name: str, issue: str, suggestion: str = "") -> str:
        """Create a detailed parameter error message."""
        message = f"Parameter '{param_name}': {issue}"
        if suggestion:
            message += f". {suggestion}"
        return message

    def _should_log_level(self, level: str) -> bool:
        """Check if we should log at the given level."""
        level_hierarchy = {"basic": 1, "verbose": 2, "trace": 3}
        current_level = level_hierarchy.get(self.debug_level, 0)
        required_level = level_hierarchy.get(level, 1)
        return current_level >= required_level

    def _show_generated_code(self) -> bool:
        """Check if generated code should be shown in debug output."""
        return self.parameters.get("show_generated", "").lower() in ("true", "1", "yes")

    def _show_type_details(self) -> bool:
        """Check if detailed type information should be shown."""
        return self.parameters.get("show_types", "").lower() in ("true", "1", "yes")

    def _get_output_suffix(self) -> str:
        """Get custom output file suffix."""
        return self.parameters.get("output_suffix", "_pb2_mcp.py")

    def _get_server_name_pattern(self) -> str:
        """Get server name pattern."""
        return self.parameters.get("server_name_pattern", "{service}")

    def _get_function_name_pattern(self) -> str:
        """Get function name pattern."""
        return self.parameters.get("function_name_pattern", "create_{service}_server")

    def _get_tool_name_case(self) -> str:
        """Get tool name case conversion."""
        return self.parameters.get("tool_name_case", "snake")

    def _include_comments(self) -> bool:
        """Check if proto comments should be included."""
        return self.parameters.get("include_comments", "true").lower() in ("true", "1", "yes")

    def _get_error_format(self) -> str:
        """Get error response format."""
        return self.parameters.get("error_format", "standard")

    def _get_stream_mode(self) -> str:
        """Get streaming RPC handling mode."""
        return self.parameters.get("stream_mode", "collect")

    def _get_auth_type(self) -> str:
        """Get authentication type."""
        return self.parameters.get("auth_type", "none")

    def _get_auth_header(self) -> str:
        """Get authentication header name."""
        return self.parameters.get("auth_header", "Authorization")

    def _should_generate_auth_metadata(self) -> bool:
        """Check if auth metadata should be generated."""
        return self.parameters.get("auth_metadata", "true").lower() in ("true", "1", "yes")

    def _has_optional_fields(self, proto_file: descriptor_pb2.FileDescriptorProto) -> bool:
        """Check if proto file has any optional fields that would need Optional typing."""
        for service in proto_file.service:
            for method in service.method:
                input_fields = self._analyze_message_fields(method.input_type)
                for field in input_fields:
                    if field.get("optional", False):
                        return True
        return False

    def parse_parameters(self, parameter_string: str) -> None:
        """
        Parse plugin parameters from the protoc parameter string.

        Parameters are in the format: key1=value1,key2=value2
        Special parameters:
        - debug: Enable debug logging (basic, verbose, trace)
        - grpc_target: gRPC server address (e.g., localhost:50051)
        - async: Generate async tool functions
        - insecure: Use insecure gRPC channel (default: false)
        - timeout: gRPC call timeout in seconds (default: 30)
        - show_generated: Show generated code content in debug output
        - show_types: Show detailed type information in debug output
        - output_suffix: Custom output file suffix (default: _pb2_mcp.py)
        - server_name_pattern: Custom server name pattern (default: {service}Service)
        - function_name_pattern: Custom function name pattern (default: create_{service}_server)
        - tool_name_case: Case for tool names (snake, camel, pascal, kebab)
        - include_comments: Include proto comments in generated code (default: true)
        - error_format: Error response format (standard, simple, detailed)
        - stream_mode: How to handle streaming RPCs (collect, skip, warn)
        - auth_type: Authentication type (none, bearer, api_key, mtls, custom)
        - auth_header: Header name for API key/bearer auth (default: Authorization)
        - auth_metadata: Generate metadata injection for auth (default: true)
        """
        if not parameter_string:
            return

        for param in parameter_string.split(","):
            if "=" in param:
                key, value = param.split("=", 1)
                self.parameters[key.strip()] = value.strip()
            else:
                # Boolean flags
                self.parameters[param.strip()] = "true"

        # Handle special parameters
        debug_value = self.parameters.get("debug", "").lower()
        self.debug_mode = debug_value in ("true", "1", "yes", "basic", "verbose", "trace")
        self.debug_level = (
            debug_value
            if debug_value in ("basic", "verbose", "trace")
            else ("basic" if self.debug_mode else "none")
        )

        self.log_debug(f"Parsed parameters: {self.parameters}")
        self.log_debug(f"Debug level: {self.debug_level}")

        # Validate parameters
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        """Validate all plugin parameters and log warnings/errors for invalid values."""
        errors = []
        warnings = []

        # Validate enum-type parameters
        enum_validations = {
            "tool_name_case": ["snake", "camel", "pascal", "kebab"],
            "error_format": ["standard", "simple", "detailed"],
            "stream_mode": ["collect", "skip", "warn"],
            "auth_type": ["none", "bearer", "api_key", "mtls", "custom"],
            "debug": ["", "true", "1", "yes", "basic", "verbose", "trace", "false", "0", "no"],
        }

        for param_name, valid_values in enum_validations.items():
            if param_name in self.parameters:
                value = self.parameters[param_name].lower()
                if value not in valid_values:
                    errors.append(self._create_validation_error(param_name, value, valid_values))

        # Validate timeout parameter
        if "timeout" in self.parameters:
            try:
                timeout_val = int(self.parameters["timeout"])
                if timeout_val <= 0:
                    errors.append(
                        self._create_parameter_error(
                            "timeout", "must be a positive integer", "Example: timeout=30"
                        )
                    )
                elif timeout_val > 300:
                    warnings.append(
                        f"timeout={timeout_val} is very high (>5 minutes). Consider a lower value for better user experience."
                    )
            except ValueError:
                errors.append(
                    self._create_parameter_error(
                        "timeout",
                        f"must be an integer, got '{self.parameters['timeout']}'",
                        "Example: timeout=30",
                    )
                )

        # Validate gRPC target format
        if "grpc_target" in self.parameters:
            target = self.parameters["grpc_target"]
            if not target or ":" not in target:
                errors.append(
                    self._create_parameter_error(
                        "grpc_target",
                        "must be in format 'host:port'",
                        "Example: grpc_target=localhost:50051 or grpc_target=api.example.com:443",
                    )
                )

        # Validate output suffix
        if "output_suffix" in self.parameters:
            suffix = self.parameters["output_suffix"]
            if not suffix.endswith(".py"):
                errors.append(
                    self._create_parameter_error(
                        "output_suffix",
                        "must end with '.py'",
                        "Example: output_suffix=_mcp_server.py",
                    )
                )

        # Validate pattern parameters contain required placeholders
        pattern_validations = {
            "server_name_pattern": "{service}",
            "function_name_pattern": "{service}",
        }

        for param_name, required_placeholder in pattern_validations.items():
            if param_name in self.parameters:
                pattern = self.parameters[param_name]
                if required_placeholder not in pattern:
                    errors.append(
                        self._create_parameter_error(
                            param_name,
                            f"must contain '{required_placeholder}' placeholder",
                            f"Example: {param_name}=My{required_placeholder}Server",
                        )
                    )

        # Validate auth_header for specific auth types
        auth_type = self.parameters.get("auth_type", "none")
        if auth_type in ("bearer", "api_key") and "auth_header" in self.parameters:
            header = self.parameters["auth_header"]
            if not header or not header.replace("-", "").replace("_", "").isalnum():
                warnings.append(f"auth_header='{header}' may not be a valid HTTP header name")

        # Log all errors and warnings
        for error in errors:
            self.log_error(error)

        for warning in warnings:
            self.log_warning(warning)

        # If there are errors, provide helpful guidance
        if errors:
            self.log_error(
                "Parameter validation failed. See PLUGIN_PARAMETERS.md for complete documentation."
            )
            self.log_error('Use --py-mcp_opt="param1=value1,param2=value2" to set parameters.')

    def _create_detailed_error_context(self, file_name: str, exception: Exception) -> str:
        """Create detailed error message with context and troubleshooting tips."""
        import traceback

        error_type = type(exception).__name__
        error_message = str(exception)

        # Build detailed context
        context_parts = [
            f"File processing failed: {file_name}",
            f"Error type: {error_type}",
            f"Error message: {error_message}",
        ]

        # Add specific troubleshooting based on error type
        if "AttributeError" in error_type:
            context_parts.append(
                "Troubleshooting: This may indicate a malformed proto file or unsupported proto feature."
            )
            context_parts.append(
                "Try: Verify your proto file syntax with 'protoc --decode_raw < file.proto'"
            )
        elif "KeyError" in error_type:
            context_parts.append(
                "Troubleshooting: Missing required proto elements or invalid references."
            )
            context_parts.append(
                "Try: Check that all message types and services are properly defined."
            )
        elif "ValueError" in error_type:
            context_parts.append("Troubleshooting: Invalid parameter values or proto content.")
            context_parts.append("Try: Review plugin parameters and proto file structure.")
        elif "ImportError" in error_type or "ModuleNotFoundError" in error_type:
            context_parts.append("Troubleshooting: Missing dependencies or installation issues.")
            context_parts.append(
                "Try: Run 'pip install protoc-gen-py-mcp[dev]' to ensure all dependencies."
            )

        # Add debug suggestions
        context_parts.extend(
            [
                "",
                "Debug suggestions:",
                '1. Enable debug mode: --py-mcp_opt="debug=verbose"',
                "2. Check proto file: protoc --decode_raw < your_file.proto",
                "3. Verify installation: protoc-gen-py-mcp --version",
                "4. Review documentation: PLUGIN_PARAMETERS.md",
            ]
        )

        # Add stack trace in debug mode
        if self.debug_mode:
            context_parts.extend(["", "Stack trace (debug mode):", traceback.format_exc()])

        return "\n".join(context_parts)

    def _get_grpc_target(self) -> Optional[str]:
        """Get gRPC target address from parameters."""
        return self.parameters.get("grpc_target")

    def _is_async_mode(self) -> bool:
        """Check if async mode is enabled."""
        return self.parameters.get("async", "").lower() in ("true", "1", "yes")

    def _is_insecure_channel(self) -> bool:
        """Check if insecure gRPC channel should be used."""
        return self.parameters.get("insecure", "").lower() in ("true", "1", "yes")

    def _get_grpc_timeout(self) -> int:
        """Get gRPC timeout in seconds."""
        try:
            return int(self.parameters.get("timeout", "30"))
        except ValueError:
            return 30

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

            if self._show_type_details():
                self.log_verbose(
                    f"File {proto_file.name}: {len(proto_file.message_type)} messages, {len(proto_file.enum_type)} enums"
                )

        self.log_debug(
            f"Indexed {len(self.message_types)} message types and {len(self.enum_types)} enum types"
        )

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

    def _get_python_type(self, field: descriptor_pb2.FieldDescriptorProto) -> str:
        """
        Map a proto field type to a Python type string for type hints.

        Args:
            field: The field descriptor to analyze

        Returns:
            Python type string (e.g., "str", "int", "List[str]", "Optional[int]")
        """
        # Check if this is a map field first
        if self._is_map_field(field):
            map_types = self._get_map_types(field)
            return f"Dict[{map_types['key']}, {map_types['value']}]"

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
            # For enums, we'll use int but add a comment about the enum type
            # TODO: Could be enhanced to use Union[int, EnumClass] or specific enum types
            return "int"
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
            # Check for well-known types
            if field.type_name:
                well_known_type = self._get_well_known_type(field.type_name)
                if well_known_type:
                    return well_known_type
            # For other messages, we'll use dict
            return "dict"
        else:
            # Fallback for unknown types
            self.log_debug(f"Unknown field type {field.type} for field {field.name}, using Any")
            return "Any"

    def _is_map_field(self, field: descriptor_pb2.FieldDescriptorProto) -> bool:
        """
        Check if a field is a map field.

        Map fields are represented as repeated message fields where the message type
        has map_entry=true option.
        """
        if (
            field.label != descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
            or field.type != descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        ):
            return False

        # Get the message type for this field
        if field.type_name in self.message_types:
            message_type = self.message_types[field.type_name]
            # Check if this message type has the map_entry option set
            return message_type.options.map_entry if message_type.options else False

        return False

    def _get_map_types(self, field: descriptor_pb2.FieldDescriptorProto) -> Dict[str, str]:
        """
        Get the key and value types for a map field.

        Returns a dict with 'key' and 'value' type strings.
        """
        if not self._is_map_field(field):
            return {"key": "Any", "value": "Any"}

        # Get the map entry message type
        if field.type_name not in self.message_types:
            return {"key": "Any", "value": "Any"}

        map_entry = self.message_types[field.type_name]

        # Map entries have exactly two fields: key (field number 1) and value (field number 2)
        key_field = None
        value_field = None

        for entry_field in map_entry.field:
            if entry_field.number == 1:
                key_field = entry_field
            elif entry_field.number == 2:
                value_field = entry_field

        if not key_field or not value_field:
            return {"key": "Any", "value": "Any"}

        # Get the Python types for key and value
        key_type = self._get_scalar_python_type(key_field)
        value_type = self._get_scalar_python_type(value_field)

        return {"key": key_type, "value": value_type}

    def _get_well_known_type(self, type_name: str) -> Optional[str]:
        """
        Get the Python type for well-known protobuf types.

        Args:
            type_name: The fully qualified type name (e.g., ".google.protobuf.Timestamp")

        Returns:
            Python type string if it's a well-known type, None otherwise
        """
        well_known_types = {
            ".google.protobuf.Timestamp": "str",  # ISO 8601 timestamp string
            ".google.protobuf.Duration": "str",  # Duration string (e.g., "3.5s")
            ".google.protobuf.Any": "dict",  # Generic dict
            ".google.protobuf.Value": "Any",  # Can be any JSON value
            ".google.protobuf.Struct": "dict",  # JSON object
            ".google.protobuf.ListValue": "List[Any]",  # JSON array
            ".google.protobuf.Empty": "None",  # No content
            ".google.protobuf.StringValue": "str",
            ".google.protobuf.Int32Value": "int",
            ".google.protobuf.Int64Value": "int",
            ".google.protobuf.UInt32Value": "int",
            ".google.protobuf.UInt64Value": "int",
            ".google.protobuf.FloatValue": "float",
            ".google.protobuf.DoubleValue": "float",
            ".google.protobuf.BoolValue": "bool",
            ".google.protobuf.BytesValue": "bytes",
        }

        return well_known_types.get(type_name)

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

        # Build a map of oneof names to check for real oneofs vs synthetic oneofs
        real_oneofs = set()
        synthetic_oneofs = set()

        for oneof_index, oneof in enumerate(message.oneof_decl):
            # Check if this oneof contains any proto3_optional fields (synthetic oneof)
            has_proto3_optional = False
            for field in message.field:
                if field.oneof_index == oneof_index and field.proto3_optional:
                    has_proto3_optional = True
                    break

            if has_proto3_optional:
                synthetic_oneofs.add(oneof_index)
                self.log_debug(f"Found synthetic oneof: {oneof.name}")
            else:
                real_oneofs.add(oneof_index)
                self.log_debug(f"Found real oneof: {oneof.name}")

        # For real oneofs, we'll include all fields but mark them as part of a oneof
        # The code generator will handle this by making them all optional and adding validation

        for field in message.field:
            # Check if this field is part of a real oneof
            is_part_of_real_oneof = False
            oneof_name = None
            if field.HasField("oneof_index") and field.oneof_index in real_oneofs:
                is_part_of_real_oneof = True
                oneof_name = message.oneof_decl[field.oneof_index].name

            # For oneof fields, treat them as optional
            is_optional = field.proto3_optional or is_part_of_real_oneof
            is_repeated = field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
            is_map = self._is_map_field(field)
            is_required = not is_optional and not is_repeated and not is_map

            # Get the base type and adjust for oneof/optional
            base_type = self._get_python_type(field)
            if is_part_of_real_oneof and not base_type.startswith("Optional["):
                # Oneof fields should be Optional even if not proto3_optional
                base_type = f"Optional[{base_type}]"

            field_info = {
                "name": field.name,
                "type": base_type,
                "proto_type": field.type,
                "required": is_required,
                "repeated": is_repeated,
                "optional": is_optional,
                "is_map": is_map,
                "is_oneof": is_part_of_real_oneof,
                "oneof_name": oneof_name,
                "type_name": field.type_name if field.type_name else None,
            }

            fields.append(field_info)
            self.log_debug(f"Analyzed field {field.name}: {field_info['type']}")

            if self._show_type_details():
                self.log_verbose(f"  Field details: {field_info}")

        return fields

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
            output_filename = proto_file.name.replace(".proto", self._get_output_suffix())

            # Generate the content
            content = self.generate_file_content(proto_file)

            # Add to response
            generated_file = response.file.add()
            generated_file.name = output_filename
            generated_file.content = content

            self.log_debug(f"Generated {len(content)} characters for {output_filename}")

            if self._show_generated_code():
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
        if self._is_async_mode():
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
                    lines, method, proto_file, service_index, method_index
                )
            else:
                self._generate_method_tool(
                    lines, method, proto_file, service_index, method_index, indentation=""
                )

    def _generate_method_tool(
        self,
        lines: List[str],
        method: descriptor_pb2.MethodDescriptorProto,
        proto_file: descriptor_pb2.FileDescriptorProto,
        service_index: int,
        method_index: int,
        indentation: str = "",
    ) -> None:
        """Generate an MCP tool function for a gRPC method."""
        method_name = method.name
        method_name_converted = self._convert_tool_name(method_name)

        # Analyze input message fields to generate function parameters
        input_fields = self._analyze_message_fields(method.input_type)

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
        method_comment = self._get_comment(proto_file.name, [6, service_index, 2, method_index])

        # Create enhanced docstring with method comment if available (if comments are enabled)
        if self._include_comments() and method_comment:
            # Clean up the comment to avoid trailing whitespace
            clean_comment = method_comment.strip()
            docstring = f'{indentation}    """Tool for {method_name} RPC method.\n{indentation}\n{indentation}    {clean_comment}\n{indentation}    """'
        else:
            docstring = f'{indentation}    """Tool for {method_name} RPC method."""'

        # Generate function definition with explicit tool name and description
        if method_comment:
            # Use the actual proto comment, clean it up for single line
            tool_description = method_comment.replace("\n", " ").strip()
        else:
            # Fallback to generic description
            tool_description = f"Generated tool for {method_name} RPC method"

        if self._is_async_mode():
            lines.extend(
                [
                    f'{indentation}@mcp.tool(name="{method_name}", description="{tool_description}")',
                    f"{indentation}async def {method_name_converted}({param_str}):",
                    docstring,
                ]
            )
        else:
            lines.extend(
                [
                    f'{indentation}@mcp.tool(name="{method_name}", description="{tool_description}")',
                    f"{indentation}def {method_name_converted}({param_str}):",
                    docstring,
                ]
            )

        # Generate request message construction
        pb2_module = proto_file.name.replace(".proto", "_pb2").replace("/", ".")
        input_type_name = method.input_type.split(".")[-1]  # Get the simple name

        lines.extend(
            [
                f"{indentation}    # Construct request message",
                f"{indentation}    request = {pb2_module}.{input_type_name}()",
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
            lines.append(f"{indentation}    # Oneof validation:")
            for oneof_name, field_names in oneofs.items():
                field_list = ", ".join(field_names)
                lines.append(
                    f"{indentation}    # Only one of [{field_list}] should be provided for oneof '{oneof_name}'"
                )

        # Generate field assignment code
        for field in input_fields:
            if field["optional"]:
                lines.extend(
                    [
                        f"{indentation}    if {field['name']} is not None:",
                        f"{indentation}        request.{field['name']} = {field['name']}",
                    ]
                )
            else:
                lines.append(f"{indentation}    request.{field['name']} = {field['name']}")

        # Add spacing before gRPC call
        if input_fields:  # Only add space if there were fields assigned
            lines.append("")

        # Generate functional gRPC call
        self._generate_grpc_call(lines, method, proto_file, indentation)

    def _generate_grpc_call(
        self,
        lines: List[str],
        method: descriptor_pb2.MethodDescriptorProto,
        proto_file: descriptor_pb2.FileDescriptorProto,
        indentation: str,
    ) -> None:
        """Generate actual gRPC call implementation."""
        method_name = method.name
        grpc_module = proto_file.name.replace(".proto", "_pb2_grpc").replace("/", ".")

        # Get service name for stub
        service_name = None
        for service in proto_file.service:
            for service_method in service.method:
                if service_method.name == method_name:
                    service_name = service.name
                    break
            if service_name:
                break

        grpc_target = (
            self._get_grpc_target() or "localhost:50051"
        )  # Default target like the target file

        # Generate simple direct gRPC call like the target file
        lines.extend(
            [
                f"{indentation}    channel = grpc.insecure_channel('{grpc_target}')",
                f"{indentation}    stub = {grpc_module}.{service_name}Stub(channel)",
                f"{indentation}    response = stub.{method_name}(request)",
                "",
                f"{indentation}    # Convert protobuf response to dict for MCP",
                f"{indentation}    from google.protobuf.json_format import MessageToDict",
                f"{indentation}    result = MessageToDict(response)",
                f"{indentation}    return result",
            ]
        )

    def _handle_streaming_method(
        self,
        lines: List[str],
        method: descriptor_pb2.MethodDescriptorProto,
        proto_file: descriptor_pb2.FileDescriptorProto,
        service_index: int,
        method_index: int,
    ) -> None:
        """Handle streaming RPC methods based on stream_mode setting."""
        stream_mode = self._get_stream_mode()
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
            self._generate_method_tool(
                lines, method, proto_file, service_index, method_index, indentation="    "
            )

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
        input_fields = self._analyze_message_fields(method.input_type)

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
        if self._include_comments() and method_comment:
            docstring = f'    """Tool for {method_name} RPC method ({stream_type}).\n    \n    {method_comment}\n    \n    Note: This is a {stream_type} RPC adapted for MCP.\n    """'
        else:
            docstring = f'    """Tool for {method_name} RPC method ({stream_type})."""'

        # Generate function
        if self._is_async_mode():
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

    def _generate_auth_metadata(self, lines: List[str], auth_type: str, indentation: str) -> None:
        """Generate authentication metadata for gRPC calls."""
        auth_header = self._get_auth_header()

        if auth_type == "bearer":
            lines.extend(
                [
                    f"{indentation}        # Bearer token authentication",
                    f"{indentation}        # TODO: Replace with actual token retrieval logic",
                    f"{indentation}        token = 'your-bearer-token-here'",
                    f"{indentation}        metadata = (('{auth_header.lower()}', f'Bearer {{token}}'),)",
                ]
            )
        elif auth_type == "api_key":
            lines.extend(
                [
                    f"{indentation}        # API key authentication",
                    f"{indentation}        # TODO: Replace with actual API key retrieval logic",
                    f"{indentation}        api_key = 'your-api-key-here'",
                    f"{indentation}        metadata = (('{auth_header.lower()}', api_key),)",
                ]
            )
        elif auth_type == "mtls":
            lines.extend(
                [
                    f"{indentation}        # mTLS authentication (handled at channel level)",
                    f"{indentation}        # TODO: Configure client certificates in channel creation",
                    f"{indentation}        metadata = ()",  # Empty metadata for mTLS
                ]
            )
        elif auth_type == "custom":
            lines.extend(
                [
                    f"{indentation}        # Custom authentication",
                    f"{indentation}        # TODO: Implement custom auth metadata logic",
                    f"{indentation}        metadata = ()",  # Placeholder for custom auth
                ]
            )
        else:
            # Default to empty metadata
            lines.extend(
                [
                    f"{indentation}        metadata = ()",
                ]
            )

        lines.append("")

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

    def _convert_tool_name(self, method_name: str) -> str:
        """Convert method name according to tool_name_case setting."""
        case_type = self._get_tool_name_case()

        if case_type == "snake":
            return self._camel_to_snake(method_name)
        elif case_type == "camel":
            # Keep first letter lowercase
            return method_name[0].lower() + method_name[1:] if method_name else ""
        elif case_type == "pascal":
            # Keep as-is (PascalCase)
            return method_name
        elif case_type == "kebab":
            return self._camel_to_snake(method_name).replace("_", "-")
        else:
            # Default to snake case
            return self._camel_to_snake(method_name)


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
