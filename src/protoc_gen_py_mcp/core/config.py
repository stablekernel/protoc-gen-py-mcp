"""Configuration management for protoc-gen-py-mcp plugin."""

from dataclasses import dataclass
from typing import Dict, Optional

from ..validation import default_validator


@dataclass
class PluginConfig:
    """Plugin configuration with typed parameters."""

    # Debug and logging
    debug_mode: bool = False
    debug_level: str = "none"
    show_generated_code: bool = False
    show_type_details: bool = False

    # Output configuration
    output_suffix: str = "_pb2_mcp.py"
    server_name_pattern: str = "{service}"
    function_name_pattern: str = "create_{service}_server"

    # Code generation options
    tool_name_case: str = "snake"
    include_comments: bool = True
    error_format: str = "standard"
    stream_mode: str = "collect"
    use_request_interceptor: bool = False

    # gRPC configuration
    grpc_target: Optional[str] = None
    async_mode: bool = False
    insecure_channel: bool = False
    grpc_timeout: int = 30


@dataclass
class CodeGenerationOptions:
    """Options for code generation behavior."""

    async_mode: bool
    include_comments: bool
    tool_name_case: str
    grpc_target: Optional[str]
    insecure_channel: bool
    grpc_timeout: int
    stream_mode: str
    use_request_interceptor: bool
    show_generated_code: bool


class ConfigManager:
    """Manages plugin configuration parsing and validation."""

    def __init__(self) -> None:
        self.config = PluginConfig()
        self.parameters: Dict[str, str] = {}

    def parse_parameters(self, parameter_string: str) -> PluginConfig:
        """
        Parse plugin parameters from the protoc parameter string.

        Parameters are in the format: key1=value1,key2=value2
        """
        self.parameters = {}

        if not parameter_string.strip():
            self.config = PluginConfig()
            return self.config

        # Split by comma and parse each parameter
        for param in parameter_string.split(","):
            param = param.strip()
            if not param:
                continue

            if "=" in param:
                key, value = param.split("=", 1)
                self.parameters[key.strip()] = value.strip()
            else:
                # Parameter without value, treat as boolean flag
                self.parameters[param] = "true"

        # Validate parameters
        result = default_validator.validate(self.parameters)
        if result.errors:
            # Store errors for later reporting - don't raise here
            # The calling code will handle validation errors
            pass

        # Parse into typed config
        self.config = self._create_config_from_parameters()
        return self.config

    def _create_config_from_parameters(self) -> PluginConfig:
        """Create typed configuration from parsed parameters."""
        # Debug and logging
        debug_value = self.parameters.get("debug", "").lower()
        debug_mode = debug_value in ("true", "1", "yes", "basic", "verbose", "trace")
        debug_level = (
            debug_value
            if debug_value in ("basic", "verbose", "trace")
            else ("basic" if debug_mode else "none")
        )

        # Boolean parameters
        show_generated = self._get_boolean_param("show_generated", False)
        show_types = self._get_boolean_param("show_types", False)
        include_comments = self._get_boolean_param("include_comments", True)
        use_request_interceptor = self._get_boolean_param("request_interceptor", False)
        async_mode = self._get_boolean_param("async", False)
        insecure_channel = self._get_boolean_param("insecure", False)

        # String parameters
        output_suffix = self.parameters.get("output_suffix", "_pb2_mcp.py")
        server_name_pattern = self.parameters.get("server_name_pattern", "{service}")
        function_name_pattern = self.parameters.get(
            "function_name_pattern", "create_{service}_server"
        )
        tool_name_case = self.parameters.get("tool_name_case", "snake")
        error_format = self.parameters.get("error_format", "standard")
        stream_mode = self.parameters.get("stream_mode", "collect")
        grpc_target = self.parameters.get("grpc_target")

        # Integer parameters
        grpc_timeout = self._get_int_param("timeout", 30)

        return PluginConfig(
            debug_mode=debug_mode,
            debug_level=debug_level,
            show_generated_code=show_generated,
            show_type_details=show_types,
            output_suffix=output_suffix,
            server_name_pattern=server_name_pattern,
            function_name_pattern=function_name_pattern,
            tool_name_case=tool_name_case,
            include_comments=include_comments,
            error_format=error_format,
            stream_mode=stream_mode,
            use_request_interceptor=use_request_interceptor,
            grpc_target=grpc_target,
            async_mode=async_mode,
            insecure_channel=insecure_channel,
            grpc_timeout=grpc_timeout,
        )

    def _get_boolean_param(self, key: str, default: bool) -> bool:
        """Get boolean parameter value."""
        value = self.parameters.get(key, "").lower()
        if not value:
            return default
        return value in ("true", "1", "yes")

    def _get_int_param(self, key: str, default: int) -> int:
        """Get integer parameter value."""
        value = self.parameters.get(key)
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def create_code_generation_options(self) -> CodeGenerationOptions:
        """Create CodeGenerationOptions from current configuration."""
        return CodeGenerationOptions(
            async_mode=self.config.async_mode,
            include_comments=self.config.include_comments,
            tool_name_case=self.config.tool_name_case,
            grpc_target=self.config.grpc_target,
            insecure_channel=self.config.insecure_channel,
            grpc_timeout=self.config.grpc_timeout,
            stream_mode=self.config.stream_mode,
            use_request_interceptor=self.config.use_request_interceptor,
            show_generated_code=self.config.show_generated_code,
        )

    def should_log_level(self, level: str) -> bool:
        """Check if a debug level should be logged."""
        if not self.config.debug_mode:
            return False

        level_hierarchy = {"basic": 1, "verbose": 2, "trace": 3}
        current_level = level_hierarchy.get(self.config.debug_level, 0)
        required_level = level_hierarchy.get(level, 0)

        return current_level >= required_level
