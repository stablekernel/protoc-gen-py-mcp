"""Unit tests for the McpPlugin class."""

import pytest
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2 as plugin

from src.protoc_gen_py_mcp.plugin import McpPlugin


class TestMcpPlugin:
    """Test cases for the McpPlugin class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()
        # Initialize TypeAnalyzer for tests
        from src.protoc_gen_py_mcp.core.type_analyzer import TypeAnalyzer

        self.plugin.type_analyzer = TypeAnalyzer(
            self.plugin.message_types, self.plugin.enum_types, self.plugin
        )

    def test_plugin_initialization(self):
        """Test that the plugin initializes correctly."""
        assert self.plugin.config is not None
        assert self.plugin.config.debug_mode is False
        assert self.plugin.message_types == {}
        assert self.plugin.enum_types == {}
        assert self.plugin.file_packages == {}

    def test_parameter_parsing(self):
        """Test parameter parsing functionality."""
        # Test empty parameters
        self.plugin.parse_parameters("")
        assert self.plugin.config.debug_mode is False
        assert self.plugin.debug_mode is False

        # Test single parameter
        self.plugin.parse_parameters("debug=true")
        assert self.plugin.config.debug_mode is True
        assert self.plugin.debug_mode is True

        # Test multiple parameters (note: output_format is not a recognized parameter)
        self.plugin.parse_parameters("debug=false,async=true")
        assert self.plugin.debug_mode is False
        assert self.plugin.config.async_mode is True

        # Test boolean flags (note: verbose is handled as debug level)
        self.plugin.parse_parameters("debug=verbose")
        assert self.plugin.debug_mode is True
        assert self.plugin.debug_level == "verbose"

    def test_scalar_python_type_mapping(self):
        """Test mapping of scalar protobuf types to Python types."""

        # Create a mock field for each type
        def create_field(field_type):
            field = descriptor_pb2.FieldDescriptorProto()
            field.type = field_type
            return field

        # Test string type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "str"

        # Test int types
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_INT32)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "int"

        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_INT64)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "int"

        # Test float types
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "float"

        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "float"

        # Test bool type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_BOOL)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "bool"

        # Test bytes type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "bytes"

        # Test enum type (not handled by get_scalar_python_type, returns "Any")
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_ENUM)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "Any"

        # Test message type (not handled by get_scalar_python_type, returns "Any")
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE)
        assert self.plugin.type_analyzer.get_scalar_python_type(field.type) == "Any"

    def test_repeated_field_types(self):
        """Test that repeated fields generate List[T] types."""
        field = descriptor_pb2.FieldDescriptorProto()
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED

        result = self.plugin.type_analyzer.get_python_type(field)
        assert result == "List[str]"

        # Test repeated int
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
        result = self.plugin.type_analyzer.get_python_type(field)
        assert result == "List[int]"

    def test_optional_field_types(self):
        """Test that proto3 optional fields generate Optional[T] types."""
        field = descriptor_pb2.FieldDescriptorProto()
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field.proto3_optional = True

        result = self.plugin.type_analyzer.get_python_type(field)
        assert result == "Optional[str]"

    def test_well_known_types(self):
        """Test well-known type mapping."""
        well_known_tests = [
            (".google.protobuf.Timestamp", "str"),
            (".google.protobuf.Duration", "str"),
            (".google.protobuf.Any", "dict"),
            (".google.protobuf.Struct", "dict"),
            (".google.protobuf.ListValue", "List[Any]"),
            (".google.protobuf.StringValue", "str"),
            (".google.protobuf.Int32Value", "int"),
            (".google.protobuf.BoolValue", "bool"),
            (".google.protobuf.Empty", "None"),
        ]

        for type_name, expected_type in well_known_tests:
            result = self.plugin.type_analyzer.get_well_known_type(type_name)
            assert (
                result == expected_type
            ), f"Expected {expected_type} for {type_name}, got {result}"

        # Test unknown type
        result = self.plugin.type_analyzer.get_well_known_type(".unknown.Type")
        assert result is None

    def test_camel_to_snake_conversion(self):
        """Test CamelCase to snake_case conversion."""
        test_cases = [
            ("CamelCase", "camel_case"),
            ("SimpleWord", "simple_word"),
            ("HTTPServer", "h_t_t_p_server"),
            ("XMLParser", "x_m_l_parser"),
            ("getName", "get_name"),
            ("setUserID", "set_user_i_d"),
            ("lowercase", "lowercase"),
            ("UPPERCASE", "u_p_p_e_r_c_a_s_e"),
        ]

        for camel, expected_snake in test_cases:
            result = self.plugin._camel_to_snake(camel)
            assert result == expected_snake, f"Expected {expected_snake}, got {result}"

    def test_output_file_suffix(self):
        """Test that the output file suffix is correct."""
        assert self.plugin.OUTPUT_FILE_SUFFIX == "_pb2_mcp.py"


class TestMessageFieldAnalysis:
    """Test cases for message field analysis."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()
        # Initialize TypeAnalyzer for tests
        from src.protoc_gen_py_mcp.core.type_analyzer import TypeAnalyzer

        self.plugin.type_analyzer = TypeAnalyzer(
            self.plugin.message_types, self.plugin.enum_types, self.plugin
        )

    def create_simple_message(self):
        """Create a simple message for testing."""
        message = descriptor_pb2.DescriptorProto()
        message.name = "TestMessage"

        # Add a string field
        field = message.field.add()
        field.name = "name"
        field.number = 1
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        # Add an int field
        field = message.field.add()
        field.name = "value"
        field.number = 2
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        return message

    def test_analyze_message_fields_not_found(self):
        """Test analyzing fields for a message type that doesn't exist."""
        result = self.plugin.type_analyzer.analyze_message_fields(".nonexistent.Message")
        assert result == []

    def test_analyze_simple_message_fields(self):
        """Test analyzing fields for a simple message."""
        # Set up the message in the type index
        message = self.create_simple_message()
        self.plugin.message_types[".test.TestMessage"] = message

        result = self.plugin.type_analyzer.analyze_message_fields(".test.TestMessage")

        assert len(result) == 2

        # Check first field
        name_field = result[0]
        assert name_field["name"] == "name"
        assert name_field["type"] == "str"
        assert name_field["required"] is True
        assert name_field["repeated"] is False
        assert name_field["optional"] is False

        # Check second field
        value_field = result[1]
        assert value_field["name"] == "value"
        assert value_field["type"] == "int"
        assert value_field["required"] is True
        assert value_field["repeated"] is False
        assert value_field["optional"] is False


class TestMcpPluginConfiguration:
    """Test plugin configuration and parameter methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()

    def test_debug_mode_parsing(self):
        """Test debug mode parsing with different values."""
        # Test debug=true
        self.plugin.parse_parameters("debug=true")
        assert self.plugin.debug_mode is True
        assert self.plugin.debug_level == "basic"

        # Test debug=verbose
        self.plugin.parse_parameters("debug=verbose")
        assert self.plugin.debug_mode is True
        assert self.plugin.debug_level == "verbose"

        # Test debug=trace
        self.plugin.parse_parameters("debug=trace")
        assert self.plugin.debug_mode is True
        assert self.plugin.debug_level == "trace"

        # Test debug=false
        self.plugin.parse_parameters("debug=false")
        assert self.plugin.debug_mode is False
        assert self.plugin.debug_level == "none"

    def test_output_suffix_configuration(self):
        """Test output suffix configuration."""
        # Test default
        assert self.plugin.config.output_suffix == "_pb2_mcp.py"

        # Test custom suffix
        self.plugin.parse_parameters("output_suffix=_custom.py")
        assert self.plugin.config.output_suffix == "_custom.py"

    def test_server_name_pattern_configuration(self):
        """Test server name pattern configuration."""
        # Test default
        assert self.plugin.config.server_name_pattern == "{service}"

        # Test custom pattern
        self.plugin.parse_parameters("server_name_pattern=My{service}Server")
        assert self.plugin.config.server_name_pattern == "My{service}Server"

    def test_function_name_pattern_configuration(self):
        """Test function name pattern configuration."""
        # Test default
        assert self.plugin.config.function_name_pattern == "create_{service}_server"

        # Test custom pattern
        self.plugin.parse_parameters("function_name_pattern=make_{service}_handler")
        assert self.plugin.config.function_name_pattern == "make_{service}_handler"

    def test_tool_name_case_configuration(self):
        """Test tool name case configuration."""
        # Test default
        assert self.plugin.config.tool_name_case == "snake"

        # Test different cases
        self.plugin.parse_parameters("tool_name_case=camel")
        assert self.plugin.config.tool_name_case == "camel"

        self.plugin.parse_parameters("tool_name_case=pascal")
        assert self.plugin.config.tool_name_case == "pascal"

        self.plugin.parse_parameters("tool_name_case=kebab")
        assert self.plugin.config.tool_name_case == "kebab"

    def test_include_comments_configuration(self):
        """Test include comments configuration."""
        # Test default (true)
        assert self.plugin.config.include_comments is True

        # Test disabled
        self.plugin.parse_parameters("include_comments=false")
        assert self.plugin.config.include_comments is False

        # Test enabled explicitly
        self.plugin.parse_parameters("include_comments=true")
        assert self.plugin.config.include_comments is True

    def test_error_format_configuration(self):
        """Test error format configuration."""
        # Test default
        assert self.plugin.config.error_format == "standard"

        # Test different formats
        self.plugin.parse_parameters("error_format=simple")
        assert self.plugin.config.error_format == "simple"

        self.plugin.parse_parameters("error_format=detailed")
        assert self.plugin.config.error_format == "detailed"

    def test_stream_mode_configuration(self):
        """Test stream mode configuration."""
        # Test default
        assert self.plugin.config.stream_mode == "collect"

        # Test different modes
        self.plugin.parse_parameters("stream_mode=skip")
        assert self.plugin.config.stream_mode == "skip"

        self.plugin.parse_parameters("stream_mode=warn")
        assert self.plugin.config.stream_mode == "warn"

    def test_request_interceptor_configuration(self):
        """Test request interceptor configuration."""
        # Test default (false)
        assert self.plugin.config.use_request_interceptor is False

        # Test enabled
        self.plugin.parse_parameters("request_interceptor=true")
        assert self.plugin.config.use_request_interceptor is True

        self.plugin.parse_parameters("request_interceptor=1")
        assert self.plugin.config.use_request_interceptor is True

        self.plugin.parse_parameters("request_interceptor=yes")
        assert self.plugin.config.use_request_interceptor is True

    def test_show_generated_code_configuration(self):
        """Test show generated code configuration."""
        # Test default (false)
        assert self.plugin.config.show_generated_code is False

        # Test enabled
        self.plugin.parse_parameters("show_generated=true")
        assert self.plugin.config.show_generated_code is True

    def test_show_type_details_configuration(self):
        """Test show type details configuration."""
        # Test default (false)
        assert self.plugin.config.show_type_details is False

        # Test enabled
        self.plugin.parse_parameters("show_types=true")
        assert self.plugin.config.show_type_details is True

    def test_should_log_level(self):
        """Test log level checking."""
        # Test with basic level
        self.plugin.parse_parameters("debug=basic")
        assert self.plugin.config_manager.should_log_level("basic") is True
        assert self.plugin.config_manager.should_log_level("verbose") is False
        assert self.plugin.config_manager.should_log_level("trace") is False

        # Test with verbose level
        self.plugin.parse_parameters("debug=verbose")
        assert self.plugin.config_manager.should_log_level("basic") is True
        assert self.plugin.config_manager.should_log_level("verbose") is True
        assert self.plugin.config_manager.should_log_level("trace") is False

        # Test with trace level
        self.plugin.parse_parameters("debug=trace")
        assert self.plugin.config_manager.should_log_level("basic") is True
        assert self.plugin.config_manager.should_log_level("verbose") is True
        assert self.plugin.config_manager.should_log_level("trace") is True

    def test_create_code_generation_options(self):
        """Test code generation options creation."""
        # Set various parameters
        self.plugin.parse_parameters(
            "async=true,include_comments=false,tool_name_case=camel,"
            "grpc_target=api.example.com:443,timeout=60,stream_mode=skip,"
            "request_interceptor=true,show_generated=true"
        )

        options = self.plugin.config_manager.create_code_generation_options()

        assert options.async_mode is True
        assert options.include_comments is False
        assert options.tool_name_case == "camel"
        assert options.grpc_target == "api.example.com:443"
        assert options.grpc_timeout == 60
        assert options.stream_mode == "skip"
        assert options.use_request_interceptor is True
        assert options.show_generated_code is True


class TestMcpPluginLogging:
    """Test plugin logging functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()

    def test_log_debug_with_levels(self, capsys):
        """Test debug logging with different levels."""
        # Test basic level logging
        self.plugin.parse_parameters("debug=basic")
        self.plugin.log_debug("test message", "basic")
        captured = capsys.readouterr()
        assert "[protoc-gen-py-mcp] test message" in captured.err

        # Clear output
        capsys.readouterr()

        # Test verbose message with basic level (should not log)
        self.plugin.log_debug("verbose message", "verbose")
        captured = capsys.readouterr()
        # Should contain parse output but not the verbose message
        assert "verbose message" not in captured.err

    def test_log_verbose(self, capsys):
        """Test verbose logging."""
        self.plugin.parse_parameters("debug=verbose")
        self.plugin.log_verbose("verbose message")
        captured = capsys.readouterr()
        assert "[protoc-gen-py-mcp] verbose message" in captured.err

    def test_log_trace(self, capsys):
        """Test trace logging."""
        self.plugin.parse_parameters("debug=trace")
        self.plugin.log_trace("trace message")
        captured = capsys.readouterr()
        assert "[protoc-gen-py-mcp] trace message" in captured.err

    def test_log_error(self, capsys):
        """Test error logging."""
        self.plugin.log_error("error message")
        captured = capsys.readouterr()
        assert "[protoc-gen-py-mcp ERROR] error message" in captured.err

    def test_log_warning(self, capsys):
        """Test warning logging."""
        self.plugin.log_warning("warning message")
        captured = capsys.readouterr()
        assert "[protoc-gen-py-mcp WARNING] warning message" in captured.err


class TestMcpPluginGrpcConfiguration:
    """Test gRPC-related configuration methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()

    def test_get_grpc_target(self):
        """Test gRPC target configuration."""
        # Test default
        assert self.plugin.config.grpc_target is None

        # Test custom target
        self.plugin.parse_parameters("grpc_target=api.example.com:443")
        assert self.plugin.config.grpc_target == "api.example.com:443"

    def test_is_async_mode(self):
        """Test async mode configuration."""
        # Test default (false)
        assert self.plugin.config.async_mode is False

        # Test enabled
        self.plugin.parse_parameters("async=true")
        assert self.plugin.config.async_mode is True

        self.plugin.parse_parameters("async=1")
        assert self.plugin.config.async_mode is True

        self.plugin.parse_parameters("async=yes")
        assert self.plugin.config.async_mode is True

    def test_is_insecure_channel(self):
        """Test insecure channel configuration."""
        # Test default (false)
        assert self.plugin.config.insecure_channel is False

        # Test enabled
        self.plugin.parse_parameters("insecure=true")
        assert self.plugin.config.insecure_channel is True

    def test_get_grpc_timeout(self):
        """Test gRPC timeout configuration."""
        # Test default
        assert self.plugin.config.grpc_timeout == 30

        # Test custom timeout
        self.plugin.parse_parameters("timeout=60")
        assert self.plugin.config.grpc_timeout == 60

        # Test invalid timeout (should default to 30)
        self.plugin.parse_parameters("timeout=invalid")
        assert self.plugin.config.grpc_timeout == 30


class TestMcpPluginUtilityMethods:
    """Test plugin utility methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()
        # Initialize TypeAnalyzer for tests
        from src.protoc_gen_py_mcp.core.type_analyzer import TypeAnalyzer

        self.plugin.type_analyzer = TypeAnalyzer(
            self.plugin.message_types, self.plugin.enum_types, self.plugin
        )

    def test_camel_to_snake_conversion(self):
        """Test camel case to snake case conversion."""
        assert self.plugin._camel_to_snake("GetUserInfo") == "get_user_info"
        assert self.plugin._camel_to_snake("SimpleMethod") == "simple_method"
        assert self.plugin._camel_to_snake("XMLParser") == "x_m_l_parser"
        assert self.plugin._camel_to_snake("lowercase") == "lowercase"
        assert self.plugin._camel_to_snake("A") == "a"
        assert self.plugin._camel_to_snake("") == ""

    def test_convert_tool_name_with_different_cases(self):
        """Test tool name conversion with different cases."""
        # Test snake case (default)
        result = self.plugin._convert_tool_name("GetUserInfo", "snake")
        assert result == "get_user_info"

        # Test camel case
        result = self.plugin._convert_tool_name("GetUserInfo", "camel")
        assert result == "getUserInfo"

        # Test pascal case
        result = self.plugin._convert_tool_name("GetUserInfo", "pascal")
        assert result == "GetUserInfo"

        # Test kebab case
        result = self.plugin._convert_tool_name("GetUserInfo", "kebab")
        assert result == "get-user-info"

        # Test invalid case (should default to snake)
        result = self.plugin._convert_tool_name("GetUserInfo", "invalid")
        assert result == "get_user_info"

    def test_has_optional_fields(self):
        """Test detection of optional fields in proto files."""
        # Create a proto file with service that uses message with optional fields
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "test.proto"
        proto_file.package = "test"

        # Add message with optional field
        message = proto_file.message_type.add()
        message.name = "TestMessage"

        field = message.field.add()
        field.name = "optional_field"
        field.number = 1
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        field.proto3_optional = True  # Mark as proto3 optional

        # Add service that uses this message as input
        service = proto_file.service.add()
        service.name = "TestService"

        method = service.method.add()
        method.name = "TestMethod"
        method.input_type = ".test.TestMessage"
        method.output_type = ".test.TestMessage"

        # Index the message so it can be found
        self.plugin._index_messages([message], "test")

        assert self.plugin.type_analyzer.has_optional_fields(proto_file) is True

        # Test proto file without optional fields
        proto_file2 = descriptor_pb2.FileDescriptorProto()
        proto_file2.name = "test2.proto"
        proto_file2.package = "test2"

        message2 = proto_file2.message_type.add()
        message2.name = "TestMessage2"

        field2 = message2.field.add()
        field2.name = "required_field"
        field2.number = 1
        field2.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field2.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Add service for the second proto
        service2 = proto_file2.service.add()
        service2.name = "TestService2"

        method2 = service2.method.add()
        method2.name = "TestMethod2"
        method2.input_type = ".test2.TestMessage2"
        method2.output_type = ".test2.TestMessage2"

        # Reset plugin state and index the second message
        self.plugin = McpPlugin()
        self.plugin._index_messages([message2], "test2")
        # Initialize TypeAnalyzer for tests after indexing
        from src.protoc_gen_py_mcp.core.type_analyzer import TypeAnalyzer

        self.plugin.type_analyzer = TypeAnalyzer(
            self.plugin.message_types, self.plugin.enum_types, self.plugin
        )

        assert self.plugin.type_analyzer.has_optional_fields(proto_file2) is False
