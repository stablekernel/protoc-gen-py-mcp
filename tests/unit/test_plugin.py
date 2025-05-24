"""Unit tests for the McpPlugin class."""

import pytest
from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf import descriptor_pb2

from src.protoc_gen_py_mcp.plugin import McpPlugin


class TestMcpPlugin:
    """Test cases for the McpPlugin class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = McpPlugin()
    
    def test_plugin_initialization(self):
        """Test that the plugin initializes correctly."""
        assert self.plugin.parameters == {}
        assert self.plugin.debug_mode is False
        assert self.plugin.message_types == {}
        assert self.plugin.enum_types == {}
        assert self.plugin.file_packages == {}
    
    def test_parameter_parsing(self):
        """Test parameter parsing functionality."""
        # Test empty parameters
        self.plugin.parse_parameters("")
        assert self.plugin.parameters == {}
        
        # Test single parameter
        self.plugin.parse_parameters("debug=true")
        assert self.plugin.parameters["debug"] == "true"
        assert self.plugin.debug_mode is True
        
        # Test multiple parameters
        self.plugin.parse_parameters("debug=false,output_format=json")
        assert self.plugin.parameters["debug"] == "false"
        assert self.plugin.parameters["output_format"] == "json"
        assert self.plugin.debug_mode is False
        
        # Test boolean flags
        self.plugin.parse_parameters("verbose")
        assert self.plugin.parameters["verbose"] == "true"
    
    def test_scalar_python_type_mapping(self):
        """Test mapping of scalar protobuf types to Python types."""
        # Create a mock field for each type
        def create_field(field_type):
            field = descriptor_pb2.FieldDescriptorProto()
            field.type = field_type
            return field
        
        # Test string type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
        assert self.plugin._get_scalar_python_type(field) == "str"
        
        # Test int types
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_INT32)
        assert self.plugin._get_scalar_python_type(field) == "int"
        
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_INT64)
        assert self.plugin._get_scalar_python_type(field) == "int"
        
        # Test float types
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)
        assert self.plugin._get_scalar_python_type(field) == "float"
        
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
        assert self.plugin._get_scalar_python_type(field) == "float"
        
        # Test bool type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_BOOL)
        assert self.plugin._get_scalar_python_type(field) == "bool"
        
        # Test bytes type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)
        assert self.plugin._get_scalar_python_type(field) == "bytes"
        
        # Test enum type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_ENUM)
        assert self.plugin._get_scalar_python_type(field) == "int"
        
        # Test message type
        field = create_field(descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE)
        assert self.plugin._get_scalar_python_type(field) == "dict"
    
    def test_repeated_field_types(self):
        """Test that repeated fields generate List[T] types."""
        field = descriptor_pb2.FieldDescriptorProto()
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
        
        result = self.plugin._get_python_type(field)
        assert result == "List[str]"
        
        # Test repeated int
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
        result = self.plugin._get_python_type(field)
        assert result == "List[int]"
    
    def test_optional_field_types(self):
        """Test that proto3 optional fields generate Optional[T] types."""
        field = descriptor_pb2.FieldDescriptorProto()
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        field.proto3_optional = True
        
        result = self.plugin._get_python_type(field)
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
            result = self.plugin._get_well_known_type(type_name)
            assert result == expected_type, f"Expected {expected_type} for {type_name}, got {result}"
        
        # Test unknown type
        result = self.plugin._get_well_known_type(".unknown.Type")
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
        result = self.plugin._analyze_message_fields(".nonexistent.Message")
        assert result == []
    
    def test_analyze_simple_message_fields(self):
        """Test analyzing fields for a simple message."""
        # Set up the message in the type index
        message = self.create_simple_message()
        self.plugin.message_types[".test.TestMessage"] = message
        
        result = self.plugin._analyze_message_fields(".test.TestMessage")
        
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