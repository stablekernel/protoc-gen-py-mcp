"""Protobuf type indexing and comment extraction for MCP code generation."""

import logging
from typing import Dict, Sequence

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2 as plugin


class ProtobufIndexer:
    """
    Handles indexing of protobuf types and extraction of comments from proto files.

    This class provides functionality to:
    - Build comprehensive type indexes for messages and enums
    - Extract and organize source code comments
    - Support nested type resolution and fully qualified naming
    """

    def __init__(self) -> None:
        """Initialize the protobuf indexer."""
        self.message_types: Dict[str, descriptor_pb2.DescriptorProto] = {}
        self.enum_types: Dict[str, descriptor_pb2.EnumDescriptorProto] = {}
        self.file_packages: Dict[str, str] = {}  # filename -> package name
        self.source_comments: Dict[str, Dict[tuple, str]] = {}  # filename -> path -> comment
        self.logger = logging.getLogger("protoc-gen-py-mcp")

    def build_type_index(self, request: plugin.CodeGeneratorRequest) -> None:
        """
        Build a comprehensive index of all types from all proto files.

        This includes both the files we're generating for and their dependencies,
        so we can resolve any type references during code generation.

        Args:
            request: The CodeGeneratorRequest containing all proto files
        """
        self.logger.debug("Building type index from all proto files")

        for proto_file in request.proto_file:
            # Store package information
            self.file_packages[proto_file.name] = proto_file.package

            # Extract comments from source code info
            self.extract_comments(proto_file)

            # Index message types
            self.index_messages(proto_file.message_type, proto_file.package)

            # Index enum types
            self.index_enums(proto_file.enum_type, proto_file.package)

        self.logger.debug(
            f"Indexed {len(self.message_types)} message types and {len(self.enum_types)} enum types"
        )

    def extract_comments(self, proto_file: descriptor_pb2.FileDescriptorProto) -> None:
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
        self.logger.debug(f"Extracted {len(comments)} comments from {proto_file.name}")

    def get_comment(self, proto_file_name: str, path: Sequence[int]) -> str:
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

    def index_messages(
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
            self.logger.debug(f"Indexed message type: {full_name}")

            # Recursively index nested messages
            if message.nested_type:
                nested_parent = f"{parent_name}.{message.name}" if parent_name else message.name
                self.index_messages(message.nested_type, package, nested_parent)

            # Index nested enums
            if message.enum_type:
                nested_parent = f"{parent_name}.{message.name}" if parent_name else message.name
                self.index_enums(message.enum_type, package, nested_parent)

    def index_enums(
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
            self.logger.debug(f"Indexed enum type: {full_name}")
