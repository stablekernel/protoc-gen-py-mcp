# protoc-gen-py-mcp TODOs

A protoc plugin that generates Python MCP server code from Protocol Buffer service definitions.

## Current Status

**✅ CORE FEATURES COMPLETE** - Production-ready plugin with comprehensive testing

The plugin successfully:
- **Generates functional gRPC client tools** with direct service calls
- **Supports async/await patterns** for modern Python development  
- **Provides extensive customization options** (naming patterns, auth, streaming, debugging)
- **Handles all proto features** (optional, repeated, maps, oneofs, enums, well-known types, streaming)
- **Includes comprehensive authentication support** via request interceptor pattern
- **Features advanced debugging capabilities** (verbose, trace levels, code output)
- **Extracts proto comments** for comprehensive tool descriptions
- **Maintains robust test suite** (101/101 tests passing, 86% coverage)

## Production Readiness Tasks

### High Priority - Enhancement & Polish
- [ ] **Troubleshooting guide** - Common issues, debugging tips, FAQ
- [ ] **Split large plugin.py file** - Break into focused modules for better maintainability

### Medium Priority - Advanced Features
- [ ] **Code generation optimization** - Performance improvements for large proto files
- [ ] **Template customization** - Allow users to override code generation templates

### Lower Priority - Research & Exploration
- [ ] **Template engine evaluation** - Consider Jinja2 for complex generation patterns (only if current approach becomes unwieldy)

## Code Quality Status

- ✅ **Linting**: flake8 passes (0 issues)
- ✅ **Formatting**: black + isort passes (consistent style)
- ✅ **Type checking**: mypy passes (basic level)
- ✅ **Tests**: 101/101 passing (100% test success)
- ✅ **Coverage**: 86% (exceeds 80% target)

## Detailed Implementation Plans

### 📋 Plan 1: Split Large plugin.py File (1366 lines → ~5 modules)

**Current Status**: Single file contains all functionality making it hard to maintain and test

**✅ Recent Progress**: Validation module already extracted (`validation.py`), dataclasses created

**Updated Target Structure** (based on current code analysis):
```
src/protoc_gen_py_mcp/
├── __init__.py
├── plugin.py              # Main orchestrator (~150 lines)
├── cli/                   # ✅ Already exists
│   ├── __init__.py
│   └── cli.py
├── validation.py          # ✅ Already extracted (97% coverage)
├── core/
│   ├── __init__.py
│   ├── config.py          # Parameter management (~300 lines)
│   ├── type_analyzer.py   # Type system analysis (~350 lines)
│   ├── code_generator.py  # Code generation (~550 lines)
│   └── utils.py           # Shared utilities (~150 lines)
```

**Implementation Steps** (updated based on current state):

1. **Phase 1: Extract Configuration Module** 
   ```python
   # core/config.py
   @dataclass
   class PluginConfig:
       # Move all 20+ parameter getters into typed dataclass
       debug_mode: bool = False
       debug_level: str = "none"
       grpc_target: Optional[str] = None
       async_mode: bool = False
       tool_name_case: str = "snake"
       stream_mode: str = "collect"
       # ... all other parameters
   
   class ConfigManager:
       def parse_parameters(self, parameter_string: str) -> PluginConfig:
       def create_code_generation_options(self, config: PluginConfig) -> CodeGenerationOptions:
   ```
   **Extract from plugin.py:**
   - Lines 173-220: `parse_parameters()` 
   - Lines 109-162: All parameter getters (`_get_*`, `_is_*`, `_show_*`, `_include_*`)
   - Lines 149-162: `_create_code_generation_options()`
   - **Benefits**: ~150 lines moved, cleaner parameter management

2. **Phase 2: Extract Type Analysis Module**
   ```python
   # core/type_analyzer.py  
   class TypeAnalyzer:
       def __init__(self, config: PluginConfig):
           self.message_types: Dict[str, DescriptorProto] = {}
           self.enum_types: Dict[str, EnumDescriptorProto] = {}
           self.source_comments: Dict[str, Dict] = {}
       
       def build_type_index(self, request: CodeGeneratorRequest) -> None:
       def analyze_message_fields(self, message_type_name: str) -> List[FieldInfo]:
       def get_python_type(self, field: FieldDescriptorProto) -> str:
   ```
   **Extract from plugin.py:**
   - Lines 320-350: `_build_type_index()` 
   - Lines 351-395: Comment extraction methods
   - Lines 396-457: Message/enum indexing (`_index_messages`, `_index_enums`)
   - Lines 458-622: Type mapping (`_get_python_type`, `_get_scalar_python_type`, `_is_map_field`, etc.)
   - Lines 623-707: `_analyze_message_fields()`
   - **Benefits**: ~350 lines moved, focused type system logic

3. **Phase 3: Extract Code Generation Module**
   ```python
   # core/code_generator.py
   class CodeGenerator:
       def __init__(self, type_analyzer: TypeAnalyzer):
           self.type_analyzer = type_analyzer
       
       def generate_file_content(self, proto_file: FileDescriptorProto, options: CodeGenerationOptions) -> str:
       def generate_service(self, service: ServiceDescriptorProto, ...) -> List[str]:
       def generate_method_tool(self, context: MethodGenerationContext, options: CodeGenerationOptions) -> List[str]:
   ```
   **Extract from plugin.py:**
   - Lines 788-814: `generate_file_content()`
   - Lines 815-888: Header/import generation (`_generate_header`, `_generate_imports`, `_generate_main_block`)
   - Lines 890-944: Service generation (`_generate_service`, `_generate_service_impl`)
   - Lines 945-1108: Method generation (`_generate_method_tool`, `_generate_grpc_call`)
   - Lines 1109-1281: Streaming support (`_handle_streaming_method`, `_generate_streaming_tool_adapted`)
   - **Benefits**: ~550 lines moved, separated generation concerns

4. **Phase 4: Extract Utilities Module**
   ```python
   # core/utils.py
   class NamingUtils:
       @staticmethod
       def camel_to_snake(name: str) -> str:
       @staticmethod 
       def convert_tool_name(method_name: str, case_type: str) -> str:
   
   class ErrorUtils:
       @staticmethod
       def create_detailed_error_context(file_name: str, exception: Exception, debug_mode: bool) -> str:
   ```
   **Extract from plugin.py:**
   - Lines 245-299: `_create_detailed_error_context()`
   - Lines 1282-1308: Naming utilities (`_camel_to_snake`, `_convert_tool_name`)
   - Lines 163-172: `_has_optional_fields()` 
   - **Benefits**: ~150 lines moved, reusable utilities

5. **Phase 5: Simplify Main Plugin**
   ```python
   # plugin.py (simplified orchestrator)
   class McpPlugin:
       def __init__(self):
           self.config_manager = ConfigManager()
           self.type_analyzer = TypeAnalyzer() 
           self.code_generator = CodeGenerator(self.type_analyzer)
       
       def generate(self, request: CodeGeneratorRequest, response: CodeGeneratorResponse) -> None:
           # Parse configuration
           config = self.config_manager.parse_parameters(request.parameter)
           
           # Build type index
           self.type_analyzer.build_type_index(request)
           
           # Generate files
           for file_name in request.file_to_generate:
               proto_file = self._find_proto_file(request, file_name)
               self.handle_file(proto_file, response, config)
       
       def handle_file(self, proto_file, response, config): 
           # Delegate to code generator
           options = self.config_manager.create_code_generation_options(config)
           content = self.code_generator.generate_file_content(proto_file, options)
           # Create response file
   ```
   **Remaining in plugin.py:**
   - Lines 65-77: Initialization and core state
   - Lines 78-101: Logging methods (keep for cross-cutting concerns)
   - Lines 709-747: Main `generate()` orchestration
   - Lines 748-787: `handle_file()` error handling
   - Lines 1311-1364: `main()` entry point
   - **Result**: ~150 lines, focused on orchestration

**Benefits of This Approach**:
- ✅ **Leverages existing work**: Builds on validation.py extraction and dataclasses
- 🎯 **Clear separation of concerns**: Config, types, generation, utilities cleanly separated  
- 🧪 **Better testability**: Each module can be unit tested independently
- 📈 **Maintainability**: ~150-550 line modules vs single 1366-line file
- 🔄 **Reusability**: Utilities and type analyzer can be reused across projects
- 🚀 **Parallel development**: Multiple developers can work on different modules
- 🔍 **Easier debugging**: Issues isolated to specific functional areas

**Migration Strategy**:
1. **Low risk**: Start with utilities (pure functions, no dependencies)  
2. **Medium risk**: Extract configuration (well-defined interface)
3. **Higher risk**: Type analyzer and code generator (more interconnected)
4. **Validate each step**: Run full test suite (101 tests) after each extraction
5. **Maintain compatibility**: Keep all public APIs unchanged during refactoring

**Estimated Effort**: 
- **Phase 1-2**: ~4-6 hours (config + utilities)
- **Phase 3-4**: ~8-12 hours (type analysis + code generation)  
- **Phase 5**: ~2-4 hours (main plugin cleanup)
- **Total**: ~14-22 hours of focused development work

**Success Criteria**:
- All 101 tests continue to pass
- `make check-all` continues to pass
- No change in generated code output
- Significant improvement in code maintainability metrics

### 📋 Plan 2: Template Engine for Code Generation

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

## Architecture Notes

The plugin uses a **single, simplified code generation approach**:
- **Direct gRPC integration** - Tools make actual gRPC service calls
- **Global MCP instances** - Clean, straightforward server pattern
- **Async support** - Modern Python async/await patterns
- **Request interceptor pattern** - Flexible authentication and middleware
- **No factory complexity** - Single clear pattern for all use cases

## Recent Achievements

### ✅ Folder Structure Reorganization
Successfully reorganized to match protoc-gen-go-mcp standards with proper package hierarchy and build system integration.

### ✅ Test Coverage Improvement (42% → 86%)
- Added 54 new tests across 4 new test files
- Comprehensive CLI, error handling, and integration tests
- All 101 tests passing with robust edge case coverage

### ✅ Parameter Validation Simplification
- Replaced 100+ lines of complex validation with declarative ValidationRule system
- Improved maintainability and testability while preserving all functionality

### ✅ Method Signature Enhancement
- Refactored method signatures using dataclasses for better type safety
- Reduced parameter complexity and improved IDE support

### ✅ Authentication Refactor
- Replaced complex auth parameters with flexible request interceptor pattern
- Better separation of concerns and user customization capabilities