# Project TODOs for protoc-gen-py-mcp

This document tracks the detailed project plan to complete the requirements for the protoc-gen-py-mcp plugin. The project aims to build a protoc plugin that generates Python MCP server code from Protocol Buffer service definitions.

## Project Overview

**Current State**: Basic protoc plugin structure exists with minimal stub generation
**Goal**: Full-featured protoc plugin that generates production-ready MCP server code using raw string concatenation

## Architecture & Core Plugin Development

### 1. Core Plugin Infrastructure
- [ ] **Refactor plugin architecture** - Move from basic stub to class-based plugin architecture following manuelzander/python-protoc-plugin pattern
- [ ] **Implement Plugin class** - Create `McpPlugin` class to encapsulate generation logic
- [ ] **Add parameter parsing** - Support protoc plugin parameters (e.g., `--py-mcp_opt=package=foo`)
- [ ] **Improve error handling** - Add proper error reporting via `CodeGeneratorResponse.error`
- [ ] **Add logging/debugging** - Include debug output for development (stderr)

### 2. Descriptor Parsing Logic
- [ ] **File dependency indexing** - Build comprehensive type index from all `request.proto_file` entries
- [ ] **Package resolution** - Properly handle proto packages and Python import paths
- [ ] **Message type parsing** - Extract and index all message types with nested type support
- [ ] **Enum type parsing** - Extract and index all enum types with value mappings
- [ ] **Service extraction** - Parse services and methods with proper metadata
- [ ] **Field analysis** - Comprehensive field parsing including labels, types, and options

### 3. Advanced Proto Feature Support
- [ ] **Proto3 optional fields** - Detect and handle `proto3_optional` correctly
- [ ] **Repeated fields** - Generate proper `List[T]` type hints and handling
- [ ] **Enum fields** - Support enum name-to-value conversion and proper typing
- [ ] **Nested messages** - Handle message fields as dict inputs with proper validation
- [ ] **Map fields** - Detect and handle proto map fields as `Dict[K, V]`
- [ ] **Oneof fields** - Handle real oneofs (non-synthetic) with proper validation
- [ ] **Well-known types** - Support common types like `Timestamp`, `Duration`, `Any`

## Code Generation Engine

### 4. String Concatenation Generator
- [ ] **Implement code builder** - Create utility class for managing indentation and line writing
- [ ] **Template structure** - Define consistent code generation patterns for all components
- [ ] **PEP8 compliance** - Ensure generated code follows Python style guidelines
- [ ] **Import management** - Smart import generation and organization
- [ ] **Comment generation** - Include helpful comments in generated code

### 5. MCP Server Code Generation
- [ ] **Factory function generation** - Create `create_<service>_server()` functions
- [ ] **Tool function generation** - Generate properly typed tool functions for each RPC method
- [ ] **Parameter conversion** - Convert proto field definitions to Python function parameters
- [ ] **Type hint generation** - Generate accurate type hints including Optional, List, Dict
- [ ] **Request message construction** - Generate code to build proto request messages from parameters
- [ ] **Response serialization** - Use `json_format.MessageToDict` for consistent JSON output
- [ ] **Multiple services support** - Handle multiple services in single proto file

### 6. Advanced Code Generation Features
- [ ] **Docstring generation** - Extract proto comments and generate Python docstrings
- [ ] **MCP tool annotations** - Add title, description, and other MCP metadata
- [ ] **Async function support** - Option to generate async tool functions
- [ ] **Error handling patterns** - Include proper exception handling in generated code
- [ ] **Validation logic** - Add input validation for required fields and constraints

## Integration & Examples

### 7. gRPC Integration Options
- [ ] **Standalone mode** - Generate self-contained MCP tools (current approach)
- [ ] **gRPC client mode** - Option to generate tools that call existing gRPC services
- [ ] **Configuration support** - Allow specifying gRPC endpoints via plugin parameters
- [ ] **Connection management** - Add proper gRPC channel lifecycle management

### 8. Example and Testing Infrastructure
- [ ] **Update example proto** - Enhance `protos/example.proto` with more complex features
- [ ] **Generate test proto files** - Create comprehensive test cases covering all features
- [ ] **Integration tests** - Test plugin output with actual protoc invocation
- [ ] **Generated code tests** - Verify generated MCP servers work correctly
- [ ] **MCP client tests** - Test tools via MCP client interactions

## Packaging & Distribution

### 9. Package Structure Improvements
- [ ] **Fix console script entry point** - Ensure `protoc-gen-py-mcp` command works correctly
- [ ] **Update pyproject.toml** - Add proper metadata, dependencies, and development tools
- [ ] **Version management** - Set up proper semantic versioning
- [ ] **License and attribution** - Add proper license headers and attribution

### 10. Build and Installation
- [ ] **Fix Makefile** - Update to use new plugin correctly
- [ ] **Installation instructions** - Update README with proper installation steps
- [ ] **Development setup** - Document development environment setup
- [ ] **Distribution testing** - Test pip installation and protoc integration

## Documentation & Usability

### 11. Documentation Complete
- [ ] **README overhaul** - Complete rewrite with proper usage examples
- [ ] **Plugin usage docs** - Document all plugin options and parameters
- [ ] **Generated code examples** - Show what the plugin produces
- [ ] **Integration guides** - How to use with existing gRPC codebases
- [ ] **Troubleshooting guide** - Common issues and solutions

### 12. Developer Experience
- [ ] **CLI debugging support** - Add verbose mode and debug output
- [ ] **Error messages** - Improve error reporting and user guidance
- [ ] **Code formatting** - Option to format generated code with black/autopep8
- [ ] **IDE integration** - Ensure generated code works well with IDEs

## Quality Assurance

### 13. Testing Strategy
- [ ] **Unit tests** - Test individual plugin components
- [ ] **Integration tests** - Test full plugin pipeline
- [ ] **Generated code tests** - Validate generated MCP servers
- [ ] **Performance tests** - Ensure plugin performs well on large proto files
- [ ] **Compatibility tests** - Test with different protoc/protobuf versions

### 14. Code Quality
- [ ] **Type hints** - Add comprehensive type hints to plugin code
- [ ] **Linting setup** - Configure flake8, mypy, and other linters
- [ ] **Code coverage** - Set up coverage reporting
- [ ] **CI/CD pipeline** - Automated testing and quality checks

## Advanced Features & Extensions

### 15. Plugin Extensibility
- [ ] **Plugin parameters** - Support for customization options
- [ ] **Template customization** - Allow custom code generation templates
- [ ] **Hook system** - Extension points for custom logic
- [ ] **Output format options** - Support different MCP server patterns

### 16. Production Features
- [ ] **Streaming RPC handling** - Decide how to handle streaming RPCs in MCP context
- [ ] **Authentication support** - Integration with gRPC auth patterns
- [ ] **Monitoring integration** - Add observability to generated servers
- [ ] **Configuration management** - Support for configuration files and environment variables

## Implementation Priority

### Phase 1: Core Functionality (High Priority)
- Items 1-5: Core plugin infrastructure and basic code generation
- Items 8-10: Basic packaging and installation

### Phase 2: Advanced Features (Medium Priority)  
- Items 6-7: Advanced code generation and gRPC integration
- Items 11-12: Complete documentation

### Phase 3: Production Ready (Lower Priority)
- Items 13-14: Testing and quality assurance
- Items 15-16: Advanced features and extensions

## Success Criteria

The project will be considered complete when:
1. Plugin generates syntactically correct, PEP8-compliant Python code
2. Generated MCP servers successfully expose gRPC service methods as tools
3. Plugin handles all common proto features (optional, repeated, enums, nested messages)
4. Installation via pip works correctly with protoc integration
5. Comprehensive documentation and examples are available
6. Test suite covers core functionality with good coverage

## Current Gaps Analysis

**What exists now:**
- Basic protoc plugin entry point in `cli.py`
- Minimal stub generation
- Console script configuration
- Example proto file and gRPC server/client

**What needs immediate attention:**
1. Complete rewrite of generation logic (currently generates minimal stubs)
2. Proper descriptor parsing (currently ignores service/method details)
3. Type-safe code generation with proper proto field handling
4. Fix plugin installation and protoc integration
5. Comprehensive testing of generated code

**Technical debt to address:**
- Fix hardcoded file suffix pattern (`_pb2_mcp.py` vs `_pb2_mpc.py` inconsistency)
- Remove placeholder code and implement real generation logic
- Update Makefile to actually use the plugin
- Add proper error handling throughout

This plan provides a roadmap for transforming the current minimal implementation into a production-ready protoc plugin that generates high-quality MCP server code from Protocol Buffer definitions.