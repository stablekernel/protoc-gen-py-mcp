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
- [ ] **Split large plugin.py file** - **🚧 IN PROGRESS: Phase 2 Complete (12% reduction achieved)**

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

### 📋 Plan 1: Split Large plugin.py File (1366 → 1137 lines, ~200 target)

**✅ Phase 1 Complete**: Utilities module extracted (`core/utils.py` - 115 lines)
**✅ Phase 2 Complete**: Configuration module extracted (`core/config.py` - 188 lines)

**Current Status**: 
- **Total Progress**: 1,366 → 1,137 lines (229 lines extracted, 17% reduction)
- **Quality**: All 101 tests passing, all quality checks passing
- **Architecture**: Type-safe configuration management with dataclasses
- **Next Target**: Extract type system (~250 lines) and code generation (~493 lines)

**Re-evaluated Target Structure** (based on current code analysis):
```
src/protoc_gen_py_mcp/
├── __init__.py
├── plugin.py              # Main orchestrator (~120 lines)
├── cli/                   # ✅ Already exists
│   ├── __init__.py
│   └── cli.py
├── validation.py          # ✅ Already extracted (97% coverage)
├── core/
│   ├── __init__.py
│   ├── config.py          # Parameter management (~200 lines)
│   ├── type_analyzer.py   # Type system analysis (~400 lines)
│   ├── code_generator.py  # Code generation (~480 lines)
│   └── utils.py           # ✅ Already extracted (115 lines)
```

**Re-evaluated Implementation Steps** (updated based on current state):

1. **✅ Phase 1: Extract Utilities Module - COMPLETED**
   - Created `core/utils.py` with NamingUtils, ErrorUtils, ProtoUtils
   - Reduced plugin.py from 1366 to 1291 lines (-75 lines)
   - All tests passing, full backward compatibility maintained

2. **✅ Phase 2: Extract Configuration Module - COMPLETED**
   - Created `core/config.py` with PluginConfig, ConfigManager, CodeGenerationOptions
   - Reduced plugin.py from 1291 to 1137 lines (-154 lines, 12% reduction)
   - Modernized configuration management with type-safe dataclasses
   - All tests updated and passing (101/101), full backward compatibility maintained
   - All quality checks passing (linting, type checking, formatting)

3. **Phase 3: Extract Type System Module** (~250 lines)
   ```python
   # core/type_analyzer.py
   class TypeAnalyzer:
       def get_python_type(self, field: FieldDescriptorProto) -> str:
       def get_scalar_python_type(self, field_type: int) -> str:
       def is_map_field(self, field: FieldDescriptorProto) -> bool:
       def get_map_types(self, field: FieldDescriptorProto) -> tuple:
       def get_well_known_type(self, type_name: str) -> str:
       def analyze_message_fields(self, message_type_name: str) -> List[FieldInfo]:
   ```
   **Extract from plugin.py:**
   - Lines 247-496: All type analysis and mapping methods  
   - Core type system logic: scalar types, maps, well-known types, field analysis
   - **Benefits**: ~250 lines moved, cleaner type system separation

4. **Phase 4: Extract Code Generation Module** (~493 lines)
   ```python
   # core/code_generator.py
   class CodeGenerator:
       def generate_file_content(self, proto_file, services) -> str:
       def generate_header(self) -> List[str]:
       def generate_imports(self, proto_file) -> List[str]:
       def generate_service(self, service, proto_file) -> List[str]:
       def generate_method_tool(self, context, options) -> None:
       def generate_grpc_call(self, method, service) -> List[str]:
       def handle_streaming_method(self, method) -> str:
   ```
   **Extract from plugin.py:**
   - Lines 577-1070: All code generation methods
   - Core generation logic: headers, imports, services, methods, streaming
   - **Benefits**: ~493 lines moved, focused code generation responsibility

**Final Result**: plugin.py reduced to ~200 lines (orchestration only)

**Updated Target Structure** (Post-Phase 2):
```
src/protoc_gen_py_mcp/
├── __init__.py
├── plugin.py              # Main orchestrator (~200 lines after Phase 4)
├── cli/                   # ✅ Already exists
│   ├── __init__.py
│   └── cli.py
├── validation.py          # ✅ Already extracted (97% coverage)
├── core/
│   ├── __init__.py
│   ├── config.py          # ✅ Parameter management (188 lines)
│   ├── type_analyzer.py   # Phase 3: Type system analysis (~250 lines)
│   ├── code_generator.py  # Phase 4: Code generation (~493 lines)
│   └── utils.py           # ✅ Already extracted (115 lines)
```

**Expected Final Results**:
- **Total extraction**: ~900+ lines from plugin.py
- **Final plugin.py**: ~200 lines (83% reduction from original 1,366 lines)
- **Modular architecture**: 6 focused modules with clear responsibilities
- **Maintainability**: Much easier to understand, test, and extend individual components

5. **Future Phase 3: Extract Type System** (Ready to implement)
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
   - Lines 66-78: Initialization and core state
   - Lines 79-108: Logging methods (keep for cross-cutting concerns)
   - Lines 652-690: Main `generate()` orchestration
   - Lines 691-730: `handle_file()` error handling
   - Lines 1225-1233: Name conversion (delegated to utils)
   - Lines 1236-1291: `main()` entry point
   - **Result**: ~120 lines, focused on orchestration

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