"""Type system analysis for protobuf to Python type mapping."""

import logging
from typing import Any, Dict, List, Optional

from google.protobuf import descriptor_pb2


class TypeAnalyzer:
    """Analyzes protobuf types and maps them to Python types."""

    def __init__(
        self,
        message_types: Dict[str, descriptor_pb2.DescriptorProto],
        enum_types: Dict[str, descriptor_pb2.EnumDescriptorProto],
        show_type_details: bool = False,
    ):
        """Initialize the type analyzer.

        Args:
            message_types: Dictionary mapping type names to message descriptors
            enum_types: Dictionary mapping type names to enum descriptors
            show_type_details: Whether to show detailed type information
        """
        self.message_types = message_types
        self.enum_types = enum_types
        self.show_type_details = show_type_details
        self.logger = logging.getLogger("protoc-gen-py-mcp")

    def get_python_type(self, field: descriptor_pb2.FieldDescriptorProto) -> str:
        """
        Get the Python type string for a protobuf field.

        Args:
            field: The field descriptor to analyze

        Returns:
            Python type string (e.g., 'str', 'int', 'List[str]', 'Dict[str, int]')
        """
        # Handle map fields
        if self.is_map_field(field):
            map_types = self.get_map_types(field)
            return f"Dict[{map_types['key']}, {map_types['value']}]"

        # Handle repeated fields
        if field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED:
            element_type = self._get_single_field_type(field)
            return f"List[{element_type}]"

        # Handle optional fields (proto3 optional)
        if field.proto3_optional:
            base_type = self._get_single_field_type(field)
            return f"Optional[{base_type}]"

        # Handle single fields
        return self._get_single_field_type(field)

    def _get_single_field_type(self, field: descriptor_pb2.FieldDescriptorProto) -> str:
        """Get the Python type for a single (non-repeated) field."""
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
            return self._get_message_type(field.type_name)
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
            return self._get_enum_type(field.type_name)
        else:
            return self.get_scalar_python_type(field.type)

    def _get_message_type(self, type_name: str) -> str:
        """Get Python type for a message field."""
        # Check for well-known types first
        well_known = self.get_well_known_type(type_name)
        if well_known:
            return well_known

        # For other messages, we'll use dict (as per original implementation)
        return "dict"

    def _get_enum_type(self, type_name: str) -> str:
        """Get Python type for an enum field."""
        # For enums, we use int type in Python
        # TODO: Could be enhanced to use Union[int, EnumClass] or specific enum types
        return "int"

    def get_scalar_python_type(self, field_type: int) -> str:
        """
        Map scalar protobuf field types to Python types.

        Args:
            field_type: The protobuf field type constant

        Returns:
            Python type string
        """
        type_mapping: Dict[int, str] = {
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

        return type_mapping.get(field_type, "Any")

    def get_well_known_type(self, type_name: str) -> Optional[str]:
        """
        Map well-known protobuf types to Python types.

        Args:
            type_name: The protobuf type name

        Returns:
            Python type string or None if not a well-known type
        """
        well_known_types = {
            ".google.protobuf.StringValue": "str",
            ".google.protobuf.Int32Value": "int",
            ".google.protobuf.Int64Value": "int",
            ".google.protobuf.UInt32Value": "int",
            ".google.protobuf.UInt64Value": "int",
            ".google.protobuf.FloatValue": "float",
            ".google.protobuf.DoubleValue": "float",
            ".google.protobuf.BoolValue": "bool",
            ".google.protobuf.BytesValue": "bytes",
            ".google.protobuf.Timestamp": "str",  # ISO format
            ".google.protobuf.Duration": "str",  # Duration string
            ".google.protobuf.Empty": "None",  # No content
            ".google.protobuf.Any": "dict",  # Generic dict
            ".google.protobuf.Struct": "dict",  # JSON object
            ".google.protobuf.Value": "Any",  # JSON value
            ".google.protobuf.ListValue": "List[Any]",  # JSON array
        }

        return well_known_types.get(type_name)

    def is_map_field(self, field: descriptor_pb2.FieldDescriptorProto) -> bool:
        """
        Check if a field is a map field.

        Args:
            field: The field descriptor to check

        Returns:
            True if the field is a map field
        """
        if (
            field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
            and field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        ):
            # Check if the message is a map entry
            message_type = self.message_types.get(field.type_name)
            if message_type and hasattr(message_type, "options"):
                return message_type.options.map_entry
        return False

    def get_map_types(self, field: descriptor_pb2.FieldDescriptorProto) -> Dict[str, str]:
        """
        Get the key and value types for a map field.

        Args:
            field: The map field descriptor

        Returns:
            Dictionary with 'key' and 'value' type strings
        """
        if not self.is_map_field(field):
            raise ValueError(f"Field {field.name} is not a map field")

        message_type = self.message_types.get(field.type_name)
        if not message_type:
            return {"key": "str", "value": "Any"}

        key_type = "str"
        value_type = "Any"

        for map_field in message_type.field:
            if map_field.name == "key":
                key_type = self.get_scalar_python_type(map_field.type)
            elif map_field.name == "value":
                if map_field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                    value_type = self._get_message_type(map_field.type_name)
                elif map_field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
                    value_type = self._get_enum_type(map_field.type_name)
                else:
                    value_type = self.get_scalar_python_type(map_field.type)

        return {"key": key_type, "value": value_type}

    def analyze_message_fields(self, message_type_name: str) -> List[Dict[str, Any]]:
        """
        Analyze message fields to extract parameter information.

        Args:
            message_type_name: The message type name to analyze

        Returns:
            List of field information dictionaries
        """
        message_type = self.message_types.get(message_type_name)
        if not message_type:
            self.logger.debug(f"Message type {message_type_name} not found in index")
            return []

        fields = []
        self.logger.debug(
            f"Analyzing message {message_type_name} with {len(message_type.field)} fields"
        )

        # Determine real oneofs vs synthetic oneofs (proto3_optional creates synthetic oneofs)
        real_oneofs = set()
        synthetic_oneofs = set()

        for oneof_index, oneof in enumerate(message_type.oneof_decl):
            # Check if this oneof contains any proto3_optional fields (synthetic oneof)
            has_proto3_optional = False
            for field in message_type.field:
                if (
                    field.HasField("oneof_index")
                    and field.oneof_index == oneof_index
                    and hasattr(field, "proto3_optional")
                    and field.proto3_optional
                ):
                    has_proto3_optional = True
                    break

            if has_proto3_optional:
                synthetic_oneofs.add(oneof_index)
                self.logger.debug(f"Found synthetic oneof: {oneof.name}")
            else:
                real_oneofs.add(oneof_index)
                self.logger.debug(f"Found real oneof: {oneof.name}")

        for field in message_type.field:
            # Check if this field is part of a real oneof
            is_part_of_real_oneof = False
            oneof_name = ""
            if field.HasField("oneof_index") and field.oneof_index in real_oneofs:
                is_part_of_real_oneof = True
                oneof_name = message_type.oneof_decl[field.oneof_index].name

            # For oneof fields, treat them as optional
            is_optional = (
                field.proto3_optional if hasattr(field, "proto3_optional") else False
            ) or is_part_of_real_oneof
            is_repeated = field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
            is_map = self.is_map_field(field)
            is_required = not is_optional and not is_repeated and not is_map

            # Get the base type and adjust for oneof/optional
            base_type = self.get_python_type(field)
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
                "is_oneof": is_part_of_real_oneof,
                "oneof_name": oneof_name,
                "is_map": is_map,
                "type_name": field.type_name if field.type_name else None,
            }

            # Handle map fields - they appear as repeated but are really maps
            if is_map:
                field_info["repeated"] = False  # Maps are not treated as repeated in API

            fields.append(field_info)
            self.logger.debug(f"Analyzed field {field.name}: {field_info['type']}")

            if self.show_type_details:
                self.logger.debug(f"  Field details: {field_info}")

        return fields

    def has_optional_fields(self, proto_file: descriptor_pb2.FileDescriptorProto) -> bool:
        """
        Check if proto file has any optional fields that would need Optional typing.

        Args:
            proto_file: The proto file descriptor

        Returns:
            True if any message in the file has optional fields
        """
        for message_type in proto_file.message_type:
            full_message_name = (
                f".{proto_file.package}.{message_type.name}"
                if proto_file.package
                else f".{message_type.name}"
            )
            fields = self.analyze_message_fields(full_message_name)

            # Check if any field is optional
            for field_info in fields:
                if field_info.get("optional", False):
                    return True

        return False
