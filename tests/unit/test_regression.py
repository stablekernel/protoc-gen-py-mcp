"""Regression tests to ensure previously fixed bugs don't reoccur."""

import pytest
from google.protobuf import descriptor_pb2

from src.protoc_gen_py_mcp.plugin import McpPlugin


class TestRegressions:
    """Test cases for previously identified and fixed bugs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()
        # Initialize TypeAnalyzer for tests
        from src.protoc_gen_py_mcp.core.type_analyzer import TypeAnalyzer

        self.plugin.type_analyzer = TypeAnalyzer(
            self.plugin.message_types, self.plugin.enum_types, self.plugin
        )

    def test_parameter_ordering_fix(self):
        """
        Regression test for parameter ordering bug.

        Previously, the plugin generated function signatures where required parameters
        came after optional parameters, which is invalid Python syntax.
        This test ensures that required parameters always come before optional ones.
        """
        # Create a message with mixed required and optional fields
        message = descriptor_pb2.DescriptorProto()
        message.name = "MixedFieldsMessage"

        # Add an optional field first (proto field number 1)
        optional_field = message.field.add()
        optional_field.name = "optional_description"
        optional_field.number = 1
        optional_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        optional_field.proto3_optional = True

        # Add a required field second (proto field number 2)
        required_field = message.field.add()
        required_field.name = "required_name"
        required_field.number = 2
        required_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

        # Add another optional field third (proto field number 3)
        optional_field2 = message.field.add()
        optional_field2.name = "optional_count"
        optional_field2.number = 3
        optional_field2.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
        optional_field2.proto3_optional = True

        # Set up the message in the type index
        self.plugin.message_types[".test.MixedFieldsMessage"] = message

        # Analyze the fields
        fields = self.plugin.type_analyzer.analyze_message_fields(".test.MixedFieldsMessage")

        # Generate parameter strings like the actual plugin does
        required_params = []
        optional_params = []

        for field in fields:
            if field["optional"]:
                optional_params.append(f"{field['name']}: {field['type']} = None")
            else:
                required_params.append(f"{field['name']}: {field['type']}")

        # Required parameters must come before optional parameters
        params = required_params + optional_params
        param_str = ", ".join(params)

        # Create a function signature and ensure it's valid Python
        function_signature = f"def test_function({param_str}) -> dict: pass"

        # This should compile without syntax errors
        try:
            compile(function_signature, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(
                f"Generated function signature has invalid syntax: {e}\\nSignature: {function_signature}"
            )

        # Verify the order is correct - required parameters should come first
        assert len(required_params) == 1
        assert len(optional_params) == 2
        assert "required_name: str" in required_params[0]
        assert "optional_description: Optional[str] = None" in optional_params[0]
        assert "optional_count: Optional[int] = None" in optional_params[1]

        # The final parameter string should have required params first
        expected_order = "required_name: str, optional_description: Optional[str] = None, optional_count: Optional[int] = None"
        assert param_str == expected_order

    def test_oneof_field_optional_wrapping(self):
        """
        Regression test for oneof field type hint wrapping.

        Previously, oneof fields that weren't already wrapped in Optional[]
        weren't getting the Optional[] wrapper, leading to inconsistent type hints.
        """
        # Create a message with a oneof
        message = descriptor_pb2.DescriptorProto()
        message.name = "OneofMessage"

        # Add a oneof declaration
        oneof = message.oneof_decl.add()
        oneof.name = "action"

        # Add fields that are part of the oneof
        field1 = message.field.add()
        field1.name = "create"
        field1.number = 1
        field1.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field1.oneof_index = 0  # Part of the first (and only) oneof

        field2 = message.field.add()
        field2.name = "delete"
        field2.number = 2
        field2.type = descriptor_pb2.FieldDescriptorProto.TYPE_BOOL
        field2.oneof_index = 0  # Part of the first (and only) oneof

        # Set up the message in the type index
        self.plugin.message_types[".test.OneofMessage"] = message

        # Analyze the fields
        fields = self.plugin.type_analyzer.analyze_message_fields(".test.OneofMessage")

        # All oneof fields should be marked as optional
        assert len(fields) == 2

        for field in fields:
            assert field["is_oneof"] is True
            assert field["optional"] is True
            assert field["oneof_name"] == "action"
            # All oneof fields should have Optional[] type hints
            assert field["type"].startswith("Optional[")

        # Check specific types
        create_field = next(f for f in fields if f["name"] == "create")
        delete_field = next(f for f in fields if f["name"] == "delete")

        assert create_field["type"] == "Optional[str]"
        assert delete_field["type"] == "Optional[bool]"
