"""Utility functions for protoc-gen-py-mcp plugin."""

import traceback
from typing import Callable

from google.protobuf import descriptor_pb2


class NamingUtils:
    """Utilities for name conversion and formatting."""

    @staticmethod
    def camel_to_snake(name: str) -> str:
        """Convert CamelCase to snake_case."""
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

    @staticmethod
    def convert_tool_name(method_name: str, case_type: str) -> str:
        """Convert method name according to specified case type."""
        if case_type == "snake":
            return NamingUtils.camel_to_snake(method_name)
        elif case_type == "camel":
            # Keep first letter lowercase
            return method_name[0].lower() + method_name[1:] if method_name else ""
        elif case_type == "pascal":
            # Keep as-is (PascalCase)
            return method_name
        elif case_type == "kebab":
            return NamingUtils.camel_to_snake(method_name).replace("_", "-")
        else:
            # Default to snake case
            return NamingUtils.camel_to_snake(method_name)


class ErrorUtils:
    """Utilities for error handling and reporting."""

    @staticmethod
    def create_detailed_error_context(
        file_name: str, exception: Exception, debug_mode: bool
    ) -> str:
        """Create detailed error message with context and troubleshooting tips."""
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
        if debug_mode:
            context_parts.extend(["", "Stack trace (debug mode):", traceback.format_exc()])

        return "\n".join(context_parts)


class ProtoUtils:
    """Utilities for working with protobuf definitions."""

    @staticmethod
    def has_optional_fields(
        proto_file: descriptor_pb2.FileDescriptorProto, analyze_message_fields_func: Callable
    ) -> bool:
        """Check if proto file has any optional fields that would need Optional typing."""
        for service in proto_file.service:
            for method in service.method:
                input_fields = analyze_message_fields_func(method.input_type)
                for field in input_fields:
                    if field.get("optional", False):
                        return True
        return False
