"""Parameter validation using declarative rules."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ValidationRule:
    """A single validation rule for a parameter."""

    field_name: str
    validator: Callable[[Any], bool]
    error_message: str
    suggestions: List[str] = field(default_factory=list)
    warning_threshold: Optional[Callable[[Any], bool]] = None
    warning_message: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of parameter validation."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0


# Validation functions
def validate_enum_value(valid_values: List[str]) -> Callable[[str], bool]:
    """Create validator for enum-like parameters."""

    def validator(value: str) -> bool:
        return value.lower() in [v.lower() for v in valid_values]

    return validator


def validate_timeout(value: str) -> bool:
    """Validate timeout parameter."""
    try:
        timeout_val = int(value)
        return 0 < timeout_val <= 300
    except ValueError:
        return False


def validate_grpc_target(value: str) -> bool:
    """Validate gRPC target format (host:port)."""
    if not value or ":" not in value:
        return False

    parts = value.split(":")
    if len(parts) != 2:
        return False

    host, port = parts
    return bool(host.strip() and port.strip())


def validate_file_extension(required_ext: str) -> Callable[[str], bool]:
    """Create validator for file extension."""

    def validator(value: str) -> bool:
        return value.endswith(required_ext)

    return validator


def validate_pattern_placeholder(required_placeholder: str) -> Callable[[str], bool]:
    """Create validator for pattern placeholders."""

    def validator(value: str) -> bool:
        return required_placeholder in value

    return validator


def timeout_warning_threshold(value: str) -> bool:
    """Check if timeout is high (warning threshold)."""
    try:
        return int(value) > 300
    except ValueError:
        return False


# Define all validation rules declaratively
VALIDATION_RULES = [
    ValidationRule(
        field_name="tool_name_case",
        validator=validate_enum_value(["snake", "camel", "pascal", "kebab"]),
        error_message="must be one of: snake, camel, pascal, kebab",
        suggestions=["tool_name_case=snake"],
    ),
    ValidationRule(
        field_name="error_format",
        validator=validate_enum_value(["standard", "simple", "detailed"]),
        error_message="must be one of: standard, simple, detailed",
        suggestions=["error_format=standard"],
    ),
    ValidationRule(
        field_name="stream_mode",
        validator=validate_enum_value(["collect", "skip", "warn"]),
        error_message="must be one of: collect, skip, warn",
        suggestions=["stream_mode=collect"],
    ),
    ValidationRule(
        field_name="debug",
        validator=validate_enum_value(
            ["", "true", "1", "yes", "basic", "verbose", "trace", "false", "0", "no"]
        ),
        error_message="must be one of: true, false, basic, verbose, trace",
        suggestions=["debug=basic", "debug=verbose"],
    ),
    ValidationRule(
        field_name="timeout",
        validator=validate_timeout,
        error_message="must be a positive integer between 1-300 seconds",
        suggestions=["timeout=30", "timeout=60"],
        warning_threshold=timeout_warning_threshold,
        warning_message="timeout is very high (>5 minutes). Consider a lower value for better user experience.",
    ),
    ValidationRule(
        field_name="grpc_target",
        validator=validate_grpc_target,
        error_message="must be in format 'host:port'",
        suggestions=["grpc_target=localhost:50051", "grpc_target=api.example.com:443"],
    ),
    ValidationRule(
        field_name="output_suffix",
        validator=validate_file_extension(".py"),
        error_message="must end with '.py'",
        suggestions=["output_suffix=_mcp_server.py"],
    ),
    ValidationRule(
        field_name="server_name_pattern",
        validator=validate_pattern_placeholder("{service}"),
        error_message="must contain '{service}' placeholder",
        suggestions=["server_name_pattern=My{service}Server"],
    ),
    ValidationRule(
        field_name="function_name_pattern",
        validator=validate_pattern_placeholder("{service}"),
        error_message="must contain '{service}' placeholder",
        suggestions=["function_name_pattern={service}Function"],
    ),
]


class ParameterValidator:
    """Generic parameter validator using declarative rules."""

    def __init__(self, rules: List[ValidationRule]):
        """Initialize with validation rules."""
        self.rules = {rule.field_name: rule for rule in rules}

    def validate(self, parameters: Dict[str, str]) -> ValidationResult:
        """Validate parameters against rules."""
        result = ValidationResult()

        for param_name, param_value in parameters.items():
            if param_name in self.rules:
                rule = self.rules[param_name]

                # Check main validation
                if not rule.validator(param_value):
                    error_msg = self._format_error(rule, param_value)
                    result.errors.append(error_msg)

                # Check warning threshold
                elif rule.warning_threshold and rule.warning_threshold(param_value):
                    warning_msg = self._format_warning(rule, param_value)
                    result.warnings.append(warning_msg)

        return result

    def _format_error(self, rule: ValidationRule, param_value: str) -> str:
        """Format validation error message."""
        message = f"Parameter '{rule.field_name}': {rule.error_message}"
        if rule.suggestions:
            suggestions = ", ".join(rule.suggestions)
            message += f". Examples: {suggestions}"
        return message

    def _format_warning(self, rule: ValidationRule, param_value: str) -> str:
        """Format validation warning message."""
        warning_msg = rule.warning_message or f"Warning for {rule.field_name}={param_value}"
        return f"{rule.field_name}={param_value}: {warning_msg}"


# Create the default validator instance
default_validator = ParameterValidator(VALIDATION_RULES)
