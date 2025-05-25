"""Integration tests for real-world scenarios."""

import tempfile
from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2 as plugin

from src.protoc_gen_py_mcp.plugin import McpPlugin


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_large_proto_file_with_many_services(self):
        """Test processing a large proto file with multiple services and complex types."""
        # Create a large, complex proto file
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "large_api.proto"
        proto_file.package = "large.api.v1"

        # Add multiple enums
        for i in range(5):
            enum = proto_file.enum_type.add()
            enum.name = f"Status{i}"
            for j in range(10):
                value = enum.value.add()
                value.name = f"VALUE_{i}_{j}"
                value.number = j

        # Add many message types with various field types
        for i in range(20):
            message = proto_file.message_type.add()
            message.name = f"Message{i}"

            # Add various field types
            for j in range(5):
                field = message.field.add()
                field.name = f"field_{j}"
                field.number = j + 1

                if j == 0:
                    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
                    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
                elif j == 1:
                    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
                    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
                elif j == 2:
                    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_BOOL
                    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
                elif j == 3:
                    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
                    field.type_name = f".large.api.v1.Status{i % 5}"
                    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
                else:
                    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
                    field.type_name = f".large.api.v1.Message{(i + 1) % 20}"
                    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        # Add multiple services with many methods
        for i in range(5):
            service = proto_file.service.add()
            service.name = f"Service{i}"

            for j in range(10):
                method = service.method.add()
                method.name = f"Method{j}"
                method.input_type = f".large.api.v1.Message{j % 20}"
                method.output_type = f".large.api.v1.Message{(j + 1) % 20}"

        # Create plugin and process
        plugin_instance = McpPlugin()
        plugin_instance.parse_parameters("debug=basic,tool_name_case=snake")

        # Build type index
        request = plugin.CodeGeneratorRequest()
        request.proto_file.append(proto_file)
        plugin_instance._build_type_index(request)

        # Generate code
        response = plugin.CodeGeneratorResponse()
        plugin_instance.handle_file(proto_file, response)

        # Verify generation succeeded
        assert response.error == ""
        assert len(response.file) == 1

        generated_content = response.file[0].content

        # Verify all services are included
        for i in range(5):
            assert f"Service{i}" in generated_content

        # Verify methods are generated with proper naming
        assert "def method0(" in generated_content
        assert "@mcp.tool" in generated_content

        # Verify imports are correct
        assert "from fastmcp import FastMCP" in generated_content
        assert "import grpc" in generated_content

    def test_request_interceptor_scenarios(self):
        """Test different request interceptor scenarios."""
        # Test with interceptor enabled
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "auth_service.proto"
        proto_file.package = "auth"

        # Add service
        service = proto_file.service.add()
        service.name = "AuthService"

        method = service.method.add()
        method.name = "Login"
        method.input_type = ".auth.LoginRequest"
        method.output_type = ".auth.LoginResponse"

        # Add messages
        request_msg = proto_file.message_type.add()
        request_msg.name = "LoginRequest"

        username_field = request_msg.field.add()
        username_field.name = "username"
        username_field.number = 1
        username_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        username_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        response_msg = proto_file.message_type.add()
        response_msg.name = "LoginResponse"

        token_field = response_msg.field.add()
        token_field.name = "token"
        token_field.number = 1
        token_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        token_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Test with interceptor enabled
        plugin_instance = McpPlugin()
        plugin_instance.parse_parameters(
            "request_interceptor=true,grpc_target=auth.example.com:443"
        )

        # Build type index
        request = plugin.CodeGeneratorRequest()
        request.proto_file.append(proto_file)
        plugin_instance._build_type_index(request)

        # Generate code
        response = plugin.CodeGeneratorResponse()
        plugin_instance.handle_file(proto_file, response)

        # Verify interceptor code is generated
        assert response.error == ""
        generated_content = response.file[0].content

        assert "default_request_interceptor" in generated_content
        assert "request_interceptor = default_request_interceptor" in generated_content
        assert "request, metadata = request_interceptor(" in generated_content
        assert "auth.example.com:443" in generated_content

    def test_streaming_rpc_handling(self):
        """Test handling of streaming RPC methods."""
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "streaming.proto"
        proto_file.package = "streaming"

        # Add messages
        request_msg = proto_file.message_type.add()
        request_msg.name = "StreamRequest"

        response_msg = proto_file.message_type.add()
        response_msg.name = "StreamResponse"

        # Add service with streaming methods
        service = proto_file.service.add()
        service.name = "StreamingService"

        # Server streaming method
        server_stream_method = service.method.add()
        server_stream_method.name = "ServerStream"
        server_stream_method.input_type = ".streaming.StreamRequest"
        server_stream_method.output_type = ".streaming.StreamResponse"
        server_stream_method.server_streaming = True

        # Client streaming method
        client_stream_method = service.method.add()
        client_stream_method.name = "ClientStream"
        client_stream_method.input_type = ".streaming.StreamRequest"
        client_stream_method.output_type = ".streaming.StreamResponse"
        client_stream_method.client_streaming = True

        # Bidirectional streaming method
        bidi_stream_method = service.method.add()
        bidi_stream_method.name = "BidiStream"
        bidi_stream_method.input_type = ".streaming.StreamRequest"
        bidi_stream_method.output_type = ".streaming.StreamResponse"
        bidi_stream_method.client_streaming = True
        bidi_stream_method.server_streaming = True

        # Regular unary method
        unary_method = service.method.add()
        unary_method.name = "UnaryMethod"
        unary_method.input_type = ".streaming.StreamRequest"
        unary_method.output_type = ".streaming.StreamResponse"

        # Test with different stream modes
        test_cases = [
            ("collect", True),  # Should generate streaming methods
            ("skip", False),  # Should skip streaming methods
            ("warn", True),  # Should generate with warnings
        ]

        for stream_mode, should_generate_streaming in test_cases:
            plugin_instance = McpPlugin()
            plugin_instance.parse_parameters(f"stream_mode={stream_mode},debug=basic")

            # Build type index
            request = plugin.CodeGeneratorRequest()
            request.proto_file.append(proto_file)
            plugin_instance._build_type_index(request)

            # Generate code
            response = plugin.CodeGeneratorResponse()
            plugin_instance.handle_file(proto_file, response)

            assert response.error == ""
            generated_content = response.file[0].content

            # Unary method should always be generated
            assert "def unary_method(" in generated_content

            if should_generate_streaming:
                # Check if streaming methods are handled
                if stream_mode == "collect":
                    # Should have streaming method implementations
                    assert (
                        "server_stream" in generated_content.lower()
                        or "# Streaming" in generated_content
                    )
            else:
                # Stream mode is skip, so streaming methods should not be generated
                assert "def server_stream(" not in generated_content
                assert "def client_stream(" not in generated_content
                assert "def bidi_stream(" not in generated_content

    def test_error_propagation_end_to_end(self):
        """Test error handling and propagation through the entire pipeline."""
        # Create proto file with intentional issues
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "error_test.proto"
        proto_file.package = "error"

        # Add service with method referencing non-existent types
        service = proto_file.service.add()
        service.name = "ErrorService"

        method = service.method.add()
        method.name = "BrokenMethod"
        method.input_type = ".error.NonExistentRequest"  # This type doesn't exist
        method.output_type = ".error.NonExistentResponse"  # This type doesn't exist

        plugin_instance = McpPlugin()
        plugin_instance.parse_parameters("debug=verbose")

        # Build type index (should handle missing types gracefully)
        request = plugin.CodeGeneratorRequest()
        request.proto_file.append(proto_file)
        plugin_instance._build_type_index(request)

        # Generate code - should handle errors gracefully
        response = plugin.CodeGeneratorResponse()
        plugin_instance.handle_file(proto_file, response)

        # Should either succeed with placeholder handling or fail gracefully
        # The plugin should not crash, but may report errors
        generated_content = response.file[0].content if response.file else ""

        # Verify that the plugin handled the missing types
        if response.error:
            # If there's an error, it should be descriptive
            assert "error" in response.error.lower()
        else:
            # If generation succeeded, check for reasonable handling
            assert "ErrorService" in generated_content

    def test_complex_nested_message_types(self):
        """Test handling of complex nested message structures."""
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "nested.proto"
        proto_file.package = "nested"

        # Create deeply nested message structure
        # Level 1: OuterMessage
        outer_msg = proto_file.message_type.add()
        outer_msg.name = "OuterMessage"

        # Level 2: OuterMessage.MiddleMessage
        middle_msg = outer_msg.nested_type.add()
        middle_msg.name = "MiddleMessage"

        # Level 3: OuterMessage.MiddleMessage.InnerMessage
        inner_msg = middle_msg.nested_type.add()
        inner_msg.name = "InnerMessage"

        # Add field to inner message
        inner_field = inner_msg.field.add()
        inner_field.name = "value"
        inner_field.number = 1
        inner_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        inner_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Add field to middle message that references inner message
        middle_field = middle_msg.field.add()
        middle_field.name = "inner"
        middle_field.number = 1
        middle_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        middle_field.type_name = ".nested.OuterMessage.MiddleMessage.InnerMessage"
        middle_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Add field to outer message that references middle message
        outer_field = outer_msg.field.add()
        outer_field.name = "middle"
        outer_field.number = 1
        outer_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        outer_field.type_name = ".nested.OuterMessage.MiddleMessage"
        outer_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED

        # Add service that uses the nested structure
        service = proto_file.service.add()
        service.name = "NestedService"

        method = service.method.add()
        method.name = "ProcessNested"
        method.input_type = ".nested.OuterMessage"
        method.output_type = ".nested.OuterMessage"

        plugin_instance = McpPlugin()
        plugin_instance.parse_parameters("debug=basic,include_comments=true")

        # Build type index
        request = plugin.CodeGeneratorRequest()
        request.proto_file.append(proto_file)
        plugin_instance._build_type_index(request)

        # Generate code
        response = plugin.CodeGeneratorResponse()
        plugin_instance.handle_file(proto_file, response)

        assert response.error == ""
        generated_content = response.file[0].content

        # Verify nested types are handled
        assert "NestedService" in generated_content
        assert "def process_nested(" in generated_content

    def test_well_known_types_handling(self):
        """Test handling of well-known protobuf types."""
        proto_file = descriptor_pb2.FileDescriptorProto()
        proto_file.name = "wellknown.proto"
        proto_file.package = "wellknown"

        # Add message with well-known types
        message = proto_file.message_type.add()
        message.name = "WellKnownMessage"

        # Timestamp field
        ts_field = message.field.add()
        ts_field.name = "timestamp"
        ts_field.number = 1
        ts_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        ts_field.type_name = ".google.protobuf.Timestamp"
        ts_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        # Duration field
        duration_field = message.field.add()
        duration_field.name = "duration"
        duration_field.number = 2
        duration_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        duration_field.type_name = ".google.protobuf.Duration"
        duration_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        # Any field
        any_field = message.field.add()
        any_field.name = "any_value"
        any_field.number = 3
        any_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        any_field.type_name = ".google.protobuf.Any"
        any_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        # StringValue field
        string_value_field = message.field.add()
        string_value_field.name = "string_value"
        string_value_field.number = 4
        string_value_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        string_value_field.type_name = ".google.protobuf.StringValue"
        string_value_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        # Add service
        service = proto_file.service.add()
        service.name = "WellKnownService"

        method = service.method.add()
        method.name = "ProcessWellKnown"
        method.input_type = ".wellknown.WellKnownMessage"
        method.output_type = ".wellknown.WellKnownMessage"

        plugin_instance = McpPlugin()
        plugin_instance.parse_parameters("debug=basic")

        # Build type index
        request = plugin.CodeGeneratorRequest()
        request.proto_file.append(proto_file)
        plugin_instance._build_type_index(request)

        # Generate code
        response = plugin.CodeGeneratorResponse()
        plugin_instance.handle_file(proto_file, response)

        assert response.error == ""
        generated_content = response.file[0].content

        # Verify well-known types are handled
        assert "WellKnownService" in generated_content
        assert "def process_well_known(" in generated_content

        # Check that the types are mapped appropriately
        # Well-known types should be handled gracefully
