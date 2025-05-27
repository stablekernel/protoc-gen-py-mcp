"""Protoc plugin for generating Python MCP server code."""

import logging
import sys
from dataclasses import dataclass
from typing import Optional, TypedDict

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2 as plugin

from .core.code_generator import CodeGenerator
from .core.config import ConfigManager, PluginConfig
from .core.logger import configure_logging
from .core.protobuf_indexer import ProtobufIndexer
from .core.type_analyzer import TypeAnalyzer
from .core.utils import ErrorUtils


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

        # Configure logging
        configure_logging(
            debug_mode=self.config.debug_mode,
            debug_level=self.config.debug_level,
        )
        self.logger = logging.getLogger("protoc-gen-py-mcp")

        # Protobuf indexer (initialized immediately)
        self.protobuf_indexer = ProtobufIndexer()

        # Type analyzer (initialized after type indexing)
        self.type_analyzer: Optional[TypeAnalyzer] = None

        # Code generator (initialized after type indexing)
        self.code_generator: Optional[CodeGenerator] = None

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

        # Update logging configuration
        configure_logging(
            debug_mode=self.config.debug_mode,
            debug_level=self.config.debug_level,
        )

        # Reinitialize protobuf indexer (in case it was created before config update)
        self.protobuf_indexer = ProtobufIndexer()

        self.logger.debug(f"Parsed configuration: {self.config}")
        self.logger.debug(f"Debug level: {self.debug_level}")

    def _create_detailed_error_context(self, file_name: str, exception: Exception) -> str:
        """Create detailed error message with context and troubleshooting tips."""
        return ErrorUtils.create_detailed_error_context(file_name, exception, self.debug_mode)

    def _build_type_index(self, request: plugin.CodeGeneratorRequest) -> None:
        """
        Build a comprehensive index of all types from all proto files.

        This includes both the files we're generating for and their dependencies,
        so we can resolve any type references during code generation.
        """
        # Delegate to protobuf indexer
        self.protobuf_indexer.build_type_index(request)

        # Show type details if requested
        if self.config.show_type_details:
            for proto_file in request.proto_file:
                self.logger.debug(
                    f"File {proto_file.name}: {len(proto_file.message_type)} messages, {len(proto_file.enum_type)} enums"
                )

        # Initialize type analyzer with indexed types
        self.type_analyzer = TypeAnalyzer(
            message_types=self.protobuf_indexer.message_types,
            enum_types=self.protobuf_indexer.enum_types,
            show_type_details=self.config.show_type_details,
        )

        # Initialize code generator
        self.code_generator = CodeGenerator(
            config=self.config,
            type_analyzer=self.type_analyzer,
        )

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

            self.logger.debug(f"Processing {len(request.file_to_generate)} files")

            # Only generate for explicitly requested files
            requested_files = set(request.file_to_generate)

            for proto_file in request.proto_file:
                if proto_file.name in requested_files:
                    self.logger.debug(f"Generating MCP code for {proto_file.name}")
                    self.handle_file(proto_file, response)
                else:
                    self.logger.debug(f"Skipping dependency file {proto_file.name}")

        except Exception as e:
            error_msg = f"Plugin error: {str(e)}"
            self.logger.error(error_msg)
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
                self.logger.debug(f"No services found in {proto_file.name}, skipping")
                return

            # Generate output filename
            output_filename = proto_file.name.replace(".proto", self.config.output_suffix)

            # Generate the content using CodeGenerator
            if self.code_generator:
                content = self.code_generator.generate_file_content(
                    proto_file, list(proto_file.service)
                )
            else:
                content = "# Error: CodeGenerator not initialized"

            # Add to response
            generated_file = response.file.add()
            generated_file.name = output_filename
            generated_file.content = content

            self.logger.debug(f"Generated {len(content)} characters for {output_filename}")

            if self.config.show_generated_code:
                self.logger.debug(f"Generated content for {output_filename}:")
                for i, line in enumerate(content.split("\n"), 1):
                    self.logger.debug(f"  {i:3d}: {line}")

        except Exception as e:
            # Create detailed error message with context
            error_context = self._create_detailed_error_context(proto_file.name, e)
            self.logger.error(error_context)
            response.error = error_context

    def _convert_tool_name(self, method_name: str, case_type: str) -> str:
        """Convert method name according to specified case type (delegation to CodeGenerator)."""
        if not self.code_generator:
            raise RuntimeError("CodeGenerator not initialized")
        return self.code_generator._convert_tool_name(method_name, case_type)


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
