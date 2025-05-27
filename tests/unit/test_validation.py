"""Tests for the declarative parameter validation system."""

import pytest

from src.protoc_gen_py_mcp.core.validation import (
    ParameterValidator,
    ValidationResult,
    ValidationRule,
    default_validator,
    validate_enum_value,
    validate_file_extension,
    validate_grpc_target,
    validate_pattern_placeholder,
    validate_timeout,
)


class TestValidationFunctions:
    """Test individual validation functions."""

    def test_validate_enum_value(self):
        """Test enum value validation."""
        validator = validate_enum_value(["snake", "camel", "pascal"])

        assert validator("snake") is True
        assert validator("camel") is True
        assert validator("SNAKE") is True  # Case insensitive
        assert validator("invalid") is False
        assert validator("") is False

    def test_validate_timeout(self):
        """Test timeout validation."""
        assert validate_timeout("30") is True
        assert validate_timeout("1") is True
        assert validate_timeout("300") is True
        assert validate_timeout("0") is False
        assert validate_timeout("-5") is False
        assert validate_timeout("301") is False
        assert validate_timeout("invalid") is False
        assert validate_timeout("") is False

    def test_validate_grpc_target(self):
        """Test gRPC target validation."""
        assert validate_grpc_target("localhost:50051") is True
        assert validate_grpc_target("api.example.com:443") is True
        assert validate_grpc_target("127.0.0.1:8080") is True
        assert validate_grpc_target("localhost") is False
        assert validate_grpc_target(":50051") is False
        assert validate_grpc_target("localhost:") is False
        assert validate_grpc_target("") is False
        assert validate_grpc_target("host:port:extra") is False

    def test_validate_file_extension(self):
        """Test file extension validation."""
        validator = validate_file_extension(".py")

        assert validator("script.py") is True
        assert validator("_mcp_server.py") is True
        assert validator("script.js") is False
        assert validator("script") is False
        assert validator("") is False

    def test_validate_pattern_placeholder(self):
        """Test pattern placeholder validation."""
        validator = validate_pattern_placeholder("{service}")

        assert validator("My{service}Server") is True
        assert validator("{service}_handler") is True
        assert validator("MyServer") is False
        assert validator("My{method}Server") is False
        assert validator("") is False


class TestValidationRule:
    """Test ValidationRule dataclass."""

    def test_basic_rule_creation(self):
        """Test creating a basic validation rule."""
        rule = ValidationRule(
            field_name="test_param",
            validator=lambda x: x == "valid",
            error_message="must be 'valid'",
        )

        assert rule.field_name == "test_param"
        assert rule.validator("valid") is True
        assert rule.validator("invalid") is False
        assert rule.error_message == "must be 'valid'"
        assert rule.suggestions == []

    def test_rule_with_suggestions(self):
        """Test rule with suggestions."""
        rule = ValidationRule(
            field_name="test_param",
            validator=lambda x: x in ["a", "b"],
            error_message="must be a or b",
            suggestions=["test_param=a", "test_param=b"],
        )

        assert rule.suggestions == ["test_param=a", "test_param=b"]

    def test_rule_with_warning_threshold(self):
        """Test rule with warning threshold."""
        rule = ValidationRule(
            field_name="timeout",
            validator=lambda x: x.isdigit() and int(x) > 0,
            error_message="must be positive integer",
            warning_threshold=lambda x: int(x) > 300,
            warning_message="value is very high",
        )

        assert rule.warning_threshold("350") is True
        assert rule.warning_threshold("30") is False
        assert rule.warning_message == "value is very high"


class TestParameterValidator:
    """Test ParameterValidator class."""

    def test_empty_parameters(self):
        """Test validation with empty parameters."""
        rules = [ValidationRule("test", lambda x: True, "error")]
        validator = ParameterValidator(rules)

        result = validator.validate({})
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_valid_parameters(self):
        """Test validation with valid parameters."""
        rules = [
            ValidationRule("param1", lambda x: x == "valid", "must be valid"),
            ValidationRule("param2", lambda x: x.isdigit(), "must be numeric"),
        ]
        validator = ParameterValidator(rules)

        result = validator.validate({"param1": "valid", "param2": "123"})
        assert result.is_valid is True
        assert result.errors == []

    def test_invalid_parameters(self):
        """Test validation with invalid parameters."""
        rules = [
            ValidationRule(
                "param1", lambda x: x == "valid", "must be valid", suggestions=["param1=valid"]
            )
        ]
        validator = ParameterValidator(rules)

        result = validator.validate({"param1": "invalid"})
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Parameter 'param1': must be valid" in result.errors[0]
        assert "param1=valid" in result.errors[0]

    def test_warning_threshold(self):
        """Test validation with warning threshold."""
        rules = [
            ValidationRule(
                "timeout",
                lambda x: x.isdigit() and int(x) > 0,
                "must be positive integer",
                warning_threshold=lambda x: int(x) > 100,
                warning_message="value is high",
            )
        ]
        validator = ParameterValidator(rules)

        result = validator.validate({"timeout": "200"})
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "timeout=200: value is high" in result.warnings[0]

    def test_unknown_parameters_ignored(self):
        """Test that unknown parameters are ignored."""
        rules = [ValidationRule("known_param", lambda x: True, "error")]
        validator = ParameterValidator(rules)

        result = validator.validate({"known_param": "value", "unknown_param": "value"})
        assert result.is_valid is True
        assert result.errors == []


class TestDefaultValidator:
    """Test the default validator instance."""

    def test_tool_name_case_validation(self):
        """Test tool_name_case validation."""
        result = default_validator.validate({"tool_name_case": "snake"})
        assert result.is_valid is True

        result = default_validator.validate({"tool_name_case": "invalid"})
        assert result.is_valid is False
        assert "tool_name_case" in result.errors[0]

    def test_timeout_validation(self):
        """Test timeout validation with default validator."""
        result = default_validator.validate({"timeout": "30"})
        assert result.is_valid is True

        result = default_validator.validate({"timeout": "0"})
        assert result.is_valid is False

        result = default_validator.validate({"timeout": "invalid"})
        assert result.is_valid is False

    def test_grpc_target_validation(self):
        """Test gRPC target validation."""
        result = default_validator.validate({"grpc_target": "localhost:50051"})
        assert result.is_valid is True

        result = default_validator.validate({"grpc_target": "invalid"})
        assert result.is_valid is False

    def test_multiple_parameter_validation(self):
        """Test validation of multiple parameters at once."""
        params = {
            "tool_name_case": "snake",
            "timeout": "30",
            "grpc_target": "localhost:50051",
            "debug": "verbose",
        }

        result = default_validator.validate(params)
        assert result.is_valid is True
        assert result.errors == []

    def test_mixed_valid_invalid_parameters(self):
        """Test validation with mix of valid and invalid parameters."""
        params = {
            "tool_name_case": "snake",  # Valid
            "timeout": "0",  # Invalid
            "grpc_target": "invalid",  # Invalid
        }

        result = default_validator.validate(params)
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert any("timeout" in error for error in result.errors)
        assert any("grpc_target" in error for error in result.errors)


class TestValidationResult:
    """Test ValidationResult class."""

    def test_empty_result(self):
        """Test empty validation result."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_result_with_errors(self):
        """Test result with errors."""
        result = ValidationResult(errors=["error1", "error2"])
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_result_with_warnings_only(self):
        """Test result with warnings but no errors."""
        result = ValidationResult(warnings=["warning1"])
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_result_with_errors_and_warnings(self):
        """Test result with both errors and warnings."""
        result = ValidationResult(errors=["error1"], warnings=["warning1"])
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
