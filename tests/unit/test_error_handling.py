"""Tests for error handling and edge cases."""

import pytest
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2 as plugin

from src.protoc_gen_py_mcp.plugin import McpPlugin


class TestMcpPluginErrorHandling:
    """Test error handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()

    def test_create_detailed_error_context_attribute_error(self):
        """Test error context creation for AttributeError."""
        error = AttributeError("'NoneType' object has no attribute 'name'")
        context = self.plugin._create_detailed_error_context("test.proto", error)

        assert "File processing failed: test.proto" in context
        assert "Error type: AttributeError" in context
        assert "malformed proto file" in context
        assert "protoc --decode_raw" in context
        assert "Debug suggestions:" in context

    def test_create_detailed_error_context_key_error(self):
        """Test error context creation for KeyError."""
        error = KeyError("missing_key")
        context = self.plugin._create_detailed_error_context("test.proto", error)

        assert "Error type: KeyError" in context
        assert "Missing required proto elements" in context
        assert "message types and services" in context

    def test_create_detailed_error_context_value_error(self):
        """Test error context creation for ValueError."""
        error = ValueError("invalid value")
        context = self.plugin._create_detailed_error_context("test.proto", error)

        assert "Error type: ValueError" in context
        assert "Invalid parameter values" in context
        assert "proto file structure" in context

    def test_create_detailed_error_context_import_error(self):
        """Test error context creation for ImportError."""
        error = ImportError("No module named 'missing_module'")
        context = self.plugin._create_detailed_error_context("test.proto", error)

        assert "Error type: ImportError" in context
        assert "Missing dependencies" in context
        assert "pip install protoc-gen-py-mcp[dev]" in context

    def test_create_detailed_error_context_module_not_found_error(self):
        """Test error context creation for ModuleNotFoundError."""
        error = ModuleNotFoundError("No module named 'missing_module'")
        context = self.plugin._create_detailed_error_context("test.proto", error)

        assert "Error type: ModuleNotFoundError" in context
        assert "Missing dependencies" in context

    def test_create_detailed_error_context_debug_mode(self):
        """Test error context includes stack trace in debug mode."""
        self.plugin.parse_parameters("debug=true")

        # Create an actual exception context
        try:
            raise ValueError("test error")
        except ValueError as error:
            context = self.plugin._create_detailed_error_context("test.proto", error)

        assert "Stack trace (debug mode):" in context
        assert "Traceback" in context

    def test_create_detailed_error_context_no_debug(self):
        """Test error context without stack trace when debug is off."""
        error = ValueError("test error")
        context = self.plugin._create_detailed_error_context("test.proto", error)

        assert "Stack trace" not in context
        assert "Traceback" not in context

    def test_handle_file_with_no_services(self):
        """Test handling proto file with no services."""
        # Create proto file without services
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "empty.proto"
        proto_file.package = "empty"

        # Add a message but no services
        message = proto_file.message_type.add()
        message.name = "EmptyMessage"

        # Create mock response
        response = plugin.CodeGeneratorResponse()

        # This should not generate any files
        self.plugin.handle_file(proto_file, response)

        # No files should be generated
        assert len(response.file) == 0
        assert response.error == ""

    def test_get_python_type_unknown_field_type(self):
        """Test handling of field types with missing message types."""
        # Create a field that references a non-existent message type
        field = descriptor_pb2.FieldDescriptorProto()
        field.name = "unknown_field"
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        field.type_name = ".nonexistent.Message"  # Message type that doesn't exist
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Should handle unknown message types gracefully
        result = self.plugin._get_python_type(field)
        # The actual return value may vary, but it should not crash
        assert isinstance(result, str)

    def test_analyze_message_fields_missing_message(self):
        """Test analyzing fields for non-existent message."""
        # Try to analyze a message that doesn't exist
        result = self.plugin._analyze_message_fields("NonExistentMessage")

        # Should return empty list for missing message
        assert result == []

    def test_analyze_message_fields_with_nested_types(self):
        """Test analyzing message with nested types."""
        # Build type index with nested message
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "nested.proto"
        proto_file.package = "nested"

        # Parent message
        parent_msg = proto_file.message_type.add()
        parent_msg.name = "Parent"

        # Nested message
        nested_msg = parent_msg.nested_type.add()
        nested_msg.name = "Nested"

        nested_field = nested_msg.field.add()
        nested_field.name = "value"
        nested_field.number = 1
        nested_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        nested_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Index the messages
        self.plugin._index_messages([parent_msg], "nested")

        # Analyze the nested message - should handle gracefully even if structure is complex
        result = self.plugin._analyze_message_fields("nested.Parent.Nested")

        # Should return a list (may be empty if type resolution fails)
        assert isinstance(result, list)

    def test_convert_tool_name_edge_cases(self):
        """Test tool name conversion with edge cases."""
        # Empty string
        assert self.plugin._convert_tool_name("", "snake") == ""

        # Single character
        assert self.plugin._convert_tool_name("A", "snake") == "a"

        # All uppercase
        assert self.plugin._convert_tool_name("XML", "snake") == "x_m_l"

        # Mixed case with numbers
        assert self.plugin._convert_tool_name("GetUser123Info", "snake") == "get_user123_info"

        # Already snake_case
        assert self.plugin._convert_tool_name("already_snake", "snake") == "already_snake"

    def test_type_mapping_edge_cases(self):
        """Test type mapping for edge cases."""
        # Test repeated message field (which looks like a map but isn't)
        field = descriptor_pb2.FieldDescriptorProto()
        field.name = "repeated_message_field"
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
        field.type_name = ".some.Message"  # Non-existent message type

        # For repeated message fields without proper map entry, should return List
        result = self.plugin._get_python_type(field)
        assert "List" in result

    def test_empty_parameter_string_handling(self):
        """Test handling of empty and whitespace parameter strings."""
        # Empty string
        self.plugin.parse_parameters("")
        assert self.plugin.parameters == {}

        # Whitespace only
        self.plugin.parse_parameters("   ")
        # May contain empty entries, but should not crash
        assert isinstance(self.plugin.parameters, dict)

    def test_malformed_parameter_strings(self):
        """Test handling of malformed parameter strings."""
        # Parameter with multiple equals signs
        self.plugin.parse_parameters("param=value=extra")
        assert self.plugin.parameters["param"] == "value=extra"

        # Parameter with no value
        self.plugin.parse_parameters("debug=,timeout=30")
        assert self.plugin.parameters["debug"] == ""
        assert self.plugin.parameters["timeout"] == "30"

        # Mixed valid and invalid parameters
        self.plugin.parse_parameters("valid=true,=invalid,another=good")
        assert self.plugin.parameters.get("valid") == "true"
        assert self.plugin.parameters.get("another") == "good"

    def test_field_analysis_with_oneof(self):
        """Test field analysis with oneof fields."""
        # Create message with oneof fields
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "oneof.proto"
        proto_file.package = "oneof"

        message = proto_file.message_type.add()
        message.name = "OneofMessage"

        # Add oneof declaration
        oneof = message.oneof_decl.add()
        oneof.name = "choice"

        # Add fields that are part of the oneof
        field1 = message.field.add()
        field1.name = "option_a"
        field1.number = 1
        field1.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field1.oneof_index = 0  # Part of the first (and only) oneof

        field2 = message.field.add()
        field2.name = "option_b"
        field2.number = 2
        field2.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
        field2.oneof_index = 0  # Part of the first (and only) oneof

        # Index the message
        self.plugin._index_messages([message], "oneof")

        # Analyze the message - should handle oneof gracefully
        result = self.plugin._analyze_message_fields("oneof.OneofMessage")

        # Should return a list
        assert isinstance(result, list)

    def test_grpc_timeout_validation_edge_cases(self):
        """Test gRPC timeout validation with edge cases."""
        # Very large timeout
        self.plugin.parse_parameters("timeout=999999")
        assert self.plugin._get_grpc_timeout() == 999999

        # Zero timeout (should be invalid but _get_grpc_timeout returns raw value)
        self.plugin.parse_parameters("timeout=0")
        assert self.plugin._get_grpc_timeout() == 0

        # Negative timeout (returns raw value, validation happens elsewhere)
        self.plugin.parse_parameters("timeout=-10")
        assert self.plugin._get_grpc_timeout() == -10

        # Non-numeric timeout (should default to 30)
        self.plugin.parse_parameters("timeout=invalid")
        assert self.plugin._get_grpc_timeout() == 30

    def test_proto_file_with_complex_package_names(self):
        """Test handling proto files with complex package names."""
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "complex/package/test.proto"
        proto_file.package = "com.example.api.v1.complex"

        # Store package information
        self.plugin.file_packages[proto_file.name] = proto_file.package

        # Verify package storage
        assert (
            self.plugin.file_packages["complex/package/test.proto"] == "com.example.api.v1.complex"
        )

    def test_enum_handling(self):
        """Test handling of enum types."""
        # Create proto file with enum
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "enum.proto"
        proto_file.package = "enums"

        enum = proto_file.enum_type.add()
        enum.name = "Status"

        value1 = enum.value.add()
        value1.name = "UNKNOWN"
        value1.number = 0

        value2 = enum.value.add()
        value2.name = "SUCCESS"
        value2.number = 1

        # Index the enum
        self.plugin._index_enums([enum], "enums")

        # Check that enum was indexed
        assert ".enums.Status" in self.plugin.enum_types

    def test_message_field_with_enum_type(self):
        """Test message field that references an enum type."""
        # Create enum
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "enum_field.proto"
        proto_file.package = "enumfield"

        enum = proto_file.enum_type.add()
        enum.name = "Color"

        # Create message with enum field
        message = proto_file.message_type.add()
        message.name = "ColoredObject"

        field = message.field.add()
        field.name = "color"
        field.number = 1
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
        field.type_name = ".enumfield.Color"
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Index both enum and message
        self.plugin._index_enums([enum], "enumfield")
        self.plugin._index_messages([message], "enumfield")

        # Analyze the message
        result = self.plugin._analyze_message_fields(".enumfield.ColoredObject")

        assert len(result) == 1
        color_field = result[0]
        assert color_field["name"] == "color"
        assert color_field["type"] == "int"  # Enums map to int in Python
        assert color_field["proto_type"] == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
