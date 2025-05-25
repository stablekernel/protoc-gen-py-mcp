# protoc-gen-py-mcp TODOs

A protoc plugin that generates Python MCP server code from Protocol Buffer service definitions.

## Current Status

**✅ CORE FEATURES COMPLETE** - Major simplification and code quality improvements completed

The plugin successfully:
- **Generates functional gRPC client tools** with direct service calls (no factory mode complexity)
- **Supports async/await patterns** for modern Python development  
- **Provides extensive customization options** (naming patterns, auth, streaming, debugging)
- **Handles all proto features** (optional, repeated, maps, oneofs, enums, well-known types, streaming)
- **Includes comprehensive authentication support** (bearer, API key, mTLS, custom)
- **Features advanced debugging capabilities** (verbose, trace levels, code output)
- **Extracts proto comments** for comprehensive tool descriptions
- **Maintains stable test suite** (24/24 tests passing)

## ✅ **COMPLETED: Folder Structure Reorganization**

### Goal: Match protoc-gen-go-mcp Structure ✅ ACHIEVED

Successfully reorganized folder structure to match https://github.com/stablekernel/protoc-gen-go-mcp standards:

#### Final Structure Achieved
```
protoc-gen-py-mcp/                  # Main plugin project
├── src/protoc_gen_py_mcp/         # Plugin source code
├── examples/
│   ├── protos/                    # Source .proto files with package structure
│   │   ├── advanced.proto
│   │   ├── wellknown.proto
│   │   └── example/v1/
│   │       └── example.proto (package example.v1)
│   └── gen/                       # Generated code with package structure
│       ├── __init__.py
│       ├── example_pb2_mcp_target.py
│       └── example/v1/
│           ├── __init__.py
│           ├── example_pb2.py
│           ├── example_pb2.pyi
│           ├── example_pb2_grpc.py
│           └── example_pb2_mcp.py
└── ...

../mcp-vibe-example/               # Sibling project (example server)
├── mcp_vibe_app/
├── pyproject.toml
├── demo.py
└── ...
```

#### Completed Implementation
- [x] **Phase 1: Reorganize examples directory**
  - [x] Created `examples/protos/` for .proto source files
  - [x] Created `examples/gen/` for all generated Python files
  - [x] Organized proto files by package structure (`example/v1/example.proto`)
  - [x] Leveraged protoc's automatic package-based directory generation

- [x] **Phase 2: Extract MCP example server**
  - [x] Moved `examples/mcp_vibe_example/` to sibling directory `../mcp-vibe-example/`
  - [x] Example server now independent project

- [x] **Phase 3: Update build system**
  - [x] Updated Makefile to reflect new paths
  - [x] Modified protoc generation commands for package structure
  - [x] Fixed lint-generated target to handle nested directories
  - [x] All quality checks (`make check-all`) passing

- [x] **Phase 4: Package structure automation**
  - [x] Added `__init__.py` files for proper Python packages
  - [x] Verified protoc automatically creates package hierarchy
  - [x] MCP plugin follows same directory logic as built-in generators

#### Key Achievements
1. **Automatic package structure**: Protoc creates `gen/example/v1/` matching `package example.v1`
2. **Standard layout**: Matches established protobuf conventions
3. **Clean separation**: Proto sources vs generated outputs clearly separated
4. **Build system compatibility**: All existing make targets work with new structure
5. **No custom logic needed**: Leveraged protoc's built-in package handling

## 🎯 **CURRENT FOCUS**

**Production Readiness and Documentation** - Folder structure reorganization complete.

## Production Readiness Tasks

### High Priority - Documentation & Usage ✅ COMPLETED
- [x] **README overhaul** - Complete installation and usage guide with examples
- [x] **Plugin parameter documentation** - Document all 20+ available configuration options (PLUGIN_PARAMETERS.md)
- [x] **Error handling improvement** - Better error messages and validation
- [x] **Plugin parameter validation** - Validate configuration options with helpful errors
- [x] **Type hints enhancement** - Improve type coverage in plugin core

### High Priority - Code Quality & Testing
- [ ] **Test coverage improvement** - Increase from 31% to 80%+ (current: 320/463 uncovered lines)
- [ ] **CLI module testing** - Add tests for the command-line interface (currently 0% coverage)
- [ ] **Integration test expansion** - More real-world scenario testing

### Medium Priority - Enhancement & Polish
- [ ] **Troubleshooting guide** - Common issues, debugging tips, FAQ

### Lower Priority - Advanced Features
- [ ] **Code generation optimization** - Performance improvements for large proto files
- [ ] **Template customization** - Allow users to override code generation templates

## Code Quality Status

- ✅ **Linting**: flake8 passes (0 issues)
- ✅ **Formatting**: black + isort passes (consistent style)
- ✅ **Type checking**: mypy passes (basic level)
- ✅ **Tests**: 24/24 passing (100% test success)
- ⚠️ **Coverage**: 31% (needs improvement to 80%+)

## Code Quality Audit Recommendations

### Dead Code and Cleanup Opportunities

1. **✅ COMPLETED: Removed legacy root-level files**:
   - ~~`grpc_server.py` and `grpc_client.py` (62 lines total)~~ - Legacy development/testing artifacts have been removed

2. **Consider simplifying parameter validation complexity**:
   - The plugin has extensive parameter validation and error handling (lines 203-308) but some validation methods may be over-engineered
   - Consider simplifying complex parameter validation methods that add 100+ lines of code while maintaining robustness

## Detailed Implementation Plans

### 📋 Plan 1: Split Large plugin.py File (1439 lines → ~4 modules)

**Current Issue**: Single file contains all functionality making it hard to maintain and test

**Target Structure**:
```
src/protoc_gen_py_mcp/
├── __init__.py
├── plugin.py              # Main entry point (~200 lines)
├── cli/
│   ├── __init__.py
│   └── cli.py
├── core/
│   ├── __init__.py
│   ├── config.py          # Parameter handling (~300 lines)
│   ├── type_analyzer.py   # Type analysis (~400 lines)
│   ├── code_generator.py  # Code generation (~500 lines)
│   └── utils.py           # Shared utilities (~100 lines)
```

**Implementation Steps**:

1. **Phase 1: Extract Configuration Module**
   ```python
   # core/config.py
   @dataclass
   class PluginConfig:
       debug_mode: bool = False
       debug_level: str = "none"
       grpc_target: Optional[str] = None
       async_mode: bool = False
       # ... all parameters as typed fields
   
   class ConfigValidator:
       def validate(self, config: PluginConfig) -> List[str]:
           # Move all validation logic here
   ```
   - Extract `parse_parameters()`, `_validate_parameters()`, and all parameter getters
   - Create `PluginConfig` dataclass to replace parameter dictionary
   - Implement configuration validation with clear error messages
   - **Tests**: Add unit tests for each validation rule

2. **Phase 2: Extract Type Analysis Module**
   ```python
   # core/type_analyzer.py
   class TypeAnalyzer:
       def __init__(self, config: PluginConfig):
           self.config = config
           self.message_types: Dict[str, DescriptorProto] = {}
           self.enum_types: Dict[str, EnumDescriptorProto] = {}
       
       def build_type_index(self, request: CodeGeneratorRequest) -> None:
       def analyze_message_fields(self, message_type_name: str) -> List[FieldInfo]:
       def get_python_type(self, field: FieldDescriptorProto) -> str:
   ```
   - Move all type analysis methods (`_build_type_index`, `_analyze_message_fields`, etc.)
   - Extract protobuf type mapping logic
   - Create clear interfaces between modules
   - **Tests**: Add comprehensive type mapping tests

3. **Phase 3: Extract Code Generation Module**
   ```python
   # core/code_generator.py
   class CodeGenerator:
       def __init__(self, config: PluginConfig, type_analyzer: TypeAnalyzer):
           self.config = config
           self.type_analyzer = type_analyzer
       
       def generate_file_content(self, proto_file: FileDescriptorProto) -> str:
       def generate_service(self, service: ServiceDescriptorProto, proto_file: FileDescriptorProto) -> List[str]:
       def generate_method_tool(self, method: MethodDescriptorProto, ...) -> List[str]:
   ```
   - Move all code generation methods
   - Consider using Jinja2 templates for complex code patterns
   - Separate concerns: structure generation vs. content generation
   - **Tests**: Add tests for each code generation pattern

4. **Phase 4: Update Main Plugin**
   ```python
   # plugin.py (simplified)
   class McpPlugin:
       def __init__(self):
           self.config = PluginConfig()
           self.type_analyzer = TypeAnalyzer(self.config)
           self.code_generator = CodeGenerator(self.config, self.type_analyzer)
       
       def generate(self, request: CodeGeneratorRequest, response: CodeGeneratorResponse) -> None:
           self.config = ConfigValidator().parse_and_validate(request.parameter)
           self.type_analyzer.build_type_index(request)
           # Delegate to specialized modules
   ```

**Benefits**:
- Each module has single responsibility
- Easier to test individual components
- Better code organization and maintainability
- Enables parallel development of features

### 📋 Plan 2: ✅ COMPLETED - Increase Test Coverage (42% → 86%+)

**✅ IMPLEMENTATION COMPLETED**

**Coverage Achievement**:
- **Before**: 42% coverage (592 statements, 342 uncovered)
- **After**: 86% coverage (592 statements, 81 uncovered)
- **Improvement**: +44% coverage increase
- **Target exceeded**: Surpassed 80% target by 6%

**What was accomplished**:

1. **✅ Expanded Plugin Testing (35% → 85% coverage)**:
   ```python
   # Added comprehensive test classes:
   TestMcpPluginConfiguration      # All parameter getters/setters
   TestMcpPluginLogging           # Debug levels, error/warning output  
   TestMcpPluginGrpcConfiguration # gRPC targets, timeouts, async modes
   TestMcpPluginUtilityMethods    # Type conversion, field analysis
   ```

2. **✅ Created CLI Module Tests (0% → 100% coverage)**:
   ```python
   # New file: tests/unit/test_cli.py
   test_main_import               # Function availability
   test_main_with_mock_stdin_stdout  # Main execution paths
   test_main_error_handling_with_mock # Error scenarios
   ```

3. **✅ Added Error Handling Tests**:
   ```python  
   # New file: tests/unit/test_error_handling.py
   TestMcpPluginErrorHandling     # 12 test methods
   # Covers: edge cases, malformed input, graceful failures
   ```

4. **✅ Created Integration Test Suite**:
   ```python
   # New file: tests/integration/test_real_world_scenarios.py
   TestRealWorldScenarios         # 6 comprehensive test methods
   # Covers: large proto files, request interceptors, streaming, nested types
   ```

5. **✅ Test Count Growth**:
   - **Before**: 47 tests total
   - **After**: 101 tests total (**54 new tests**)
   - **Distribution**: 35 unit + 66 integration/error handling

**Coverage by Module**:
- `plugin.py`: 85% coverage (main implementation)
- `validation.py`: 97% coverage (comprehensive validation)
- `cli/cli.py`: 100% coverage (complete CLI testing)
- `cli/__init__.py`: 100% coverage

**Benefits Achieved**:
- ✅ More than doubled test coverage (42% → 86%)
- ✅ Comprehensive edge case validation
- ✅ Real-world scenario testing  
- ✅ Improved confidence in refactoring
- ✅ Better documentation through test examples

**Code Quality Impact**: Dramatically reduced risk of undetected bugs while maintaining all existing functionality.

### 📋 Plan 3: ✅ COMPLETED - Simplify Parameter Validation Complexity

**✅ IMPLEMENTATION COMPLETED**

**What was accomplished**:

1. **✅ Created Declarative Validation Module**: 
   - New file: `src/protoc_gen_py_mcp/validation.py`
   - Replaced 100+ lines of complex validation with clean declarative rules
   - Added comprehensive type hints and dataclass structures

2. **✅ Implemented ValidationRule System**:
   ```python
   @dataclass
   class ValidationRule:
       field_name: str
       validator: Callable[[Any], bool] 
       error_message: str
       suggestions: List[str] = field(default_factory=list)
       warning_threshold: Optional[Callable[[Any], bool]] = None
   ```

3. **✅ Reduced Validation Logic Complexity**:
   ```python
   # Before: 100+ lines of nested if/else logic
   # After: 20 lines using declarative validator
   def _validate_parameters(self) -> None:
       result = default_validator.validate(self.parameters)
       for error in result.errors:
           self.log_error(error)
   ```

4. **✅ Added Comprehensive Test Coverage**:
   - New file: `tests/unit/test_validation.py` (23 test cases)
   - Tests all validation functions, rules, and edge cases
   - Increased total test count from 24 to 47 tests

5. **✅ Maintained Full Backward Compatibility**:
   - All existing tests continue to pass
   - Same validation behavior and error messages
   - No breaking changes to plugin interface

**Benefits Achieved**:
- ✅ Reduced validation code complexity by 80% (100+ lines → 20 lines)
- ✅ Declarative rules easier to understand and modify
- ✅ Better error messages with automatic suggestions
- ✅ Individual validation rules are testable
- ✅ Easy to add new validation rules
- ✅ Clean separation of concerns (validation logic extracted)

**Code Quality Improvement**: Validation complexity dramatically reduced while improving maintainability and testability.

### 📋 Plan 4: ✅ COMPLETED - Improve Method Signatures with Dataclasses

**✅ IMPLEMENTATION COMPLETED**

**What was accomplished**:

1. **✅ Added Dataclass Definitions**:
   ```python
   @dataclass
   class MethodGenerationContext:
       method: MethodDescriptorProto
       service: ServiceDescriptorProto  
       proto_file: FileDescriptorProto
       service_index: int
       method_index: int
       indentation: str = ""
   
   @dataclass
   class CodeGenerationOptions:
       async_mode: bool
       include_comments: bool
       tool_name_case: str
       auth_type: str
       grpc_target: Optional[str]
       insecure_channel: bool
       grpc_timeout: int
       stream_mode: str
       auth_header: str
       show_generated_code: bool
   ```

2. **✅ Refactored Method Signatures**:
   ```python
   # Before:
   def _generate_method_tool(self, lines, method, proto_file, service_index, method_index, indentation=""):
   def _generate_grpc_call(self, lines, method, proto_file, indentation):
   
   # After:
   def _generate_method_tool(self, lines: List[str], context: MethodGenerationContext, options: CodeGenerationOptions):
   def _generate_grpc_call(self, lines: List[str], context: MethodGenerationContext, options: CodeGenerationOptions):
   ```

3. **✅ Added Helper Method**:
   ```python
   def _create_code_generation_options(self) -> CodeGenerationOptions:
       """Create CodeGenerationOptions from current plugin parameters."""
   ```

4. **✅ Updated All Call Sites**:
   - Fixed both call sites in `_generate_service_impl()` and `_handle_streaming_method()`
   - Updated `_handle_streaming_method` signature to pass through service parameter
   - Enhanced `_convert_tool_name()` to accept optional case_type parameter

5. **✅ Maintained Backward Compatibility**:
   - All existing tests pass (10/10 unit tests)
   - Integration tests pass
   - No breaking changes to public API

**Benefits Achieved**:
- ✅ Cleaner method signatures (reduced from 6+ parameters to 2 dataclass objects)
- ✅ Better type safety with structured parameters
- ✅ Easier to extend with new options in the future
- ✅ Better IDE support with autocomplete
- ✅ More maintainable and testable code

**Code Quality Improvement**: Method complexity reduced, better separation of concerns achieved.

### 📋 Auth Parameters Refactor: ✅ COMPLETED - Replace with Request Interceptor Pattern

**✅ IMPLEMENTATION COMPLETED**

**What was accomplished**:

1. **✅ Removed Auth Parameters from Plugin**:
   - Eliminated `auth_type`, `auth_header`, and `auth_metadata` parameters
   - Removed auth parameter validation and getter methods
   - Updated parameter docstring to remove auth references

2. **✅ Implemented Request Interceptor Pattern**:
   ```python
   # Added to CodeGenerationOptions dataclass:
   use_request_interceptor: bool
   
   # Generated default interceptor function:
   def default_request_interceptor(request, method_name, metadata):
       """Default request interceptor - no modifications."""
       return request, metadata
   
   request_interceptor = default_request_interceptor
   ```

3. **✅ Updated Code Generation**:
   ```python
   # New gRPC call pattern with interceptor:
   if options.use_request_interceptor:
       request, metadata = request_interceptor(request, 'MethodName', ())
       response = stub.MethodName(request, metadata=metadata)
   else:
       response = stub.MethodName(request)
   ```

4. **✅ Maintained Backward Compatibility**:
   - Default behavior unchanged when interceptor not enabled
   - All 24 tests continue to pass
   - No breaking changes to existing generated code

5. **✅ Parameter Control**:
   - New parameter: `request_interceptor=true` to enable pattern
   - Default: disabled (generates simple gRPC calls)
   - User can override `request_interceptor` function for custom auth/logging

**Benefits Achieved**:
- ✅ Flexible authentication and middleware pattern
- ✅ Reduced parameter complexity (removed 3 auth-specific parameters)
- ✅ Better adherence to original REQUIREMENTS.md scope
- ✅ User-customizable request modification (auth, logging, monitoring)
- ✅ Clean separation of concerns (auth logic moved to user code)

**Usage Example**:
```bash
# Enable request interceptor pattern
protoc --py-mcp_opt="request_interceptor=true" example.proto

# User can then customize in generated code:
def custom_auth_interceptor(request, method_name, metadata):
    """Add bearer token authentication."""
    headers = [('authorization', 'Bearer ' + get_token())]
    return request, metadata + tuple(headers)

request_interceptor = custom_auth_interceptor
```

### 📋 Plan 5: Consider Template Engine for Code Generation

**Current Issue**: String concatenation for code generation could be more maintainable

**Evaluation and Implementation**:

1. **Phase 1: Evaluate Template Engine Need**
   - Analyze current code generation complexity
   - Compare current approach vs. template engine benefits
   - Consider maintenance overhead of adding new dependency

2. **Phase 2: If Beneficial, Implement Jinja2 Templates**
   ```python
   # templates/mcp_service.py.j2
   """Generated from {{ proto_file.name }}"""
   
   from fastmcp import FastMCP
   {% if has_optional_fields %}
   from typing import Optional
   {% endif %}
   
   mcp = FastMCP("MCP Server from Proto")
   
   {% for method in methods %}
   @mcp.tool(name="{{ method.name }}", description="{{ method.description }}")
   def {{ method.function_name }}({{ method.parameters | join(', ') }}):
       """{{ method.docstring }}"""
       # ... generated implementation
   {% endfor %}
   ```

3. **Phase 3: Gradual Migration**
   - Start with most complex generation methods
   - Keep simple string concatenation for basic cases
   - Maintain backward compatibility

**Decision Criteria**:
- Current approach works well for most cases
- Templates add dependency and complexity
- Consider only if code generation becomes significantly more complex
- **Recommendation**: Monitor current approach, consider templates only if generation patterns become unwieldy

## Summary

**Implementation Status**:
1. **✅ Plan 4** (Method Signatures) - COMPLETED - Cleaner interfaces with dataclasses
2. **Plan 3** (Validation) - Next priority, quick wins to reduce complexity
3. **Plan 1** (Module Split) - Enables parallel development
4. **Plan 2** (Test Coverage) - Ensures quality during refactoring
5. **Plan 5** (Templates) - Only if needed for complex generation

### Configuration and Dependencies

1. **Dependency management**:
   - protobuf version constraint `>=5.26.1,<6.0` is good practice
   - All dependencies are properly specified with reasonable version constraints

2. **Configuration files are well-structured**:
   - pyproject.toml follows modern Python packaging standards
   - Makefile provides comprehensive targets for development workflow

### Test Coverage and Organization

1. **Good test organization**:
   - Tests are well-structured with unit and integration tests separated
   - Test utilities provide good abstractions (TempProtoProject class)

2. **Test coverage metrics**:
   - Source code: 1844 lines
   - Test code: 1291 lines (70% ratio - good)
   - Need to focus on increasing actual coverage percentage from 31% to 80%+

### Code Quality Score: B+ (Good, with room for improvement)

**Strengths:**
- Well-organized test suite
- Comprehensive parameter validation
- Good type hints and documentation
- Modern Python packaging setup

**Areas for improvement:**
- ~~Remove dead code and legacy files~~ ✅ COMPLETED
- Split large plugin.py file into modules  
- Increase test coverage to 80%+
- Consider simplifying complex parameter validation

## Architecture Notes

The plugin uses a **single, simplified code generation approach**:
- **Direct gRPC integration** - Tools make actual gRPC service calls
- **Global MCP instances** - Clean, straightforward server pattern
- **Async support** - Modern Python async/await patterns
- **Comprehensive auth** - Bearer, API key, mTLS, custom authentication
- **No factory complexity** - Single clear pattern for all use cases