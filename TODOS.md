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

## Recent Major Changes ✅ COMPLETED

### Code Simplification (Latest)
- [x] **Factory mode removal** - Eliminated dual-mode complexity, simplified to single approach
- [x] **Code cleanup** - Removed 200+ lines of unused factory code and mode references  
- [x] **Quality improvements** - All linting, formatting, and type checking now passes
- [x] **Test updates** - All tests updated and passing with simplified approach

## Remaining Tasks

### High Priority - Production Readiness

#### Documentation & Usage (CRITICAL)
- [ ] **README overhaul** - Complete installation and usage guide with examples
- [ ] **Plugin parameter documentation** - Document all 20+ available configuration options
- [ ] **Quick start guide** - Simple tutorial from proto to working MCP server
- [ ] **Generated code examples** - Show real-world usage patterns and integration
- [ ] **Integration guides** - How to connect with existing gRPC services

#### Code Quality & Testing
- [ ] **Test coverage improvement** - Increase from 31% to 80%+ (current: 320/463 uncovered lines)
- [ ] **CLI module testing** - Add tests for the command-line interface (currently 0% coverage)
- [ ] **Integration test expansion** - More real-world scenario testing
- [ ] **Performance benchmarks** - Test with large proto files and complex services

### Medium Priority - Enhancement & Polish

#### Developer Experience  
- [ ] **Troubleshooting guide** - Common issues, debugging tips, FAQ
- [ ] **VS Code integration** - Syntax highlighting for generated code
- [ ] **Plugin development guide** - How to extend and customize the plugin

#### Code Improvements
- [ ] **Type hints enhancement** - Improve type coverage in plugin core (currently basic)
- [ ] **Error handling improvement** - Better error messages and validation
- [ ] **Plugin parameter validation** - Validate configuration options with helpful errors
- [ ] **Comment extraction enhancement** - Better handling of proto documentation

### Lower Priority - Advanced Features

#### Platform & Compatibility
- [ ] **CI/CD pipeline** - Automated testing, quality checks, and releases
- [ ] **Cross-platform testing** - Ensure compatibility across OS platforms  
- [ ] **Protoc version compatibility** - Test with different protoc/protobuf versions
- [ ] **Python version testing** - Verify compatibility across Python 3.10-3.12+

#### Advanced Functionality
- [ ] **Code generation optimization** - Performance improvements for large proto files
- [ ] **Plugin composition** - Support for multiple plugins in single protoc run
- [ ] **Template customization** - Allow users to override code generation templates
- [ ] **Incremental generation** - Only regenerate changed services

## Success Criteria

✅ **Core Implementation Complete:**
1. Plugin generates syntactically correct, PEP8-compliant Python code
2. Generated MCP servers successfully expose gRPC methods as functional tools
3. Plugin handles all common proto features without factory mode complexity
4. All linting, formatting, and type checking passes
5. Test suite covers core functionality (24 tests passing)

⏳ **Remaining for Production Release:**
6. Comprehensive documentation and installation guides
7. Test coverage above 80% threshold
8. Performance validation with large proto files

## 🎯 **CURRENT FOCUS**

**Documentation and Production Readiness** - The core plugin is feature-complete and stable.

Priority tasks:
1. **Update README** with complete installation and usage instructions
2. **Improve test coverage** from 31% to 80%+ 
3. **Document all plugin parameters** and configuration options
4. **Create quick start guide** for new users

## Code Quality Status

- ✅ **Linting**: flake8 passes (0 issues)
- ✅ **Formatting**: black + isort passes (consistent style)
- ✅ **Type checking**: mypy passes (basic level)
- ✅ **Tests**: 24/24 passing (100% test success)
- ⚠️ **Coverage**: 31% (needs improvement to 80%+)

## Architecture Notes

The plugin now uses a **single, simplified code generation approach**:
- **Direct gRPC integration** - Tools make actual gRPC service calls
- **Global MCP instances** - Clean, straightforward server pattern
- **Async support** - Modern Python async/await patterns
- **Comprehensive auth** - Bearer, API key, mTLS, custom authentication
- **No factory complexity** - Removed dual-mode confusion, single clear pattern

This represents a **major simplification** while maintaining all functionality.

## 🚀 **NEW PRIORITY: Self-Contained MCP-gRPC Example Application**

### Single Executable MCP-gRPC Integration Demo

**Goal**: Create a single executable Python application that embeds both the gRPC server implementation and the generated MCP server, demonstrating the complete workflow in one process.

#### Implementation Plan

##### Phase 1: Integrated Application Design ✨ HIGH PRIORITY
- [ ] **Application architecture design**
  - [ ] Single Python executable with embedded gRPC server
  - [ ] Threading model: gRPC server in background thread
  - [ ] FastMCP server in main thread (stdio communication)
  - [ ] Graceful shutdown and error handling

- [ ] **Executable packaging**
  - [ ] Create `mcp-vibe` executable using setuptools entry point
  - [ ] Bundle all dependencies for standalone operation
  - [ ] Cross-platform compatibility (Linux, macOS, Windows)
  - [ ] Add to PATH for easy MCP client integration

##### Phase 2: Application Implementation
- [ ] **Integrated server creation**
  - [ ] Embed VibeService implementation directly in MCP app
  - [ ] Start gRPC server on background thread (localhost:50051)
  - [ ] Modify generated MCP code to use embedded gRPC server
  - [ ] Ensure proper initialization order and error handling

- [ ] **Application entry point**
  - [ ] Create main application that starts both servers
  - [ ] Background thread for gRPC server management
  - [ ] Foreground FastMCP server for MCP protocol
  - [ ] Proper signal handling and cleanup
  - [ ] Configuration options (debug mode, custom port)

- [ ] **Code integration strategy**
  - [ ] Import and embed the VibeService class
  - [ ] Use generated example_pb2_mcp code as base
  - [ ] Modify connection logic to use in-process gRPC
  - [ ] Add retry logic for gRPC connection during startup

##### Phase 3: Packaging & Distribution
- [ ] **Python packaging**
  - [ ] Setup.py/pyproject.toml with console script entry point
  - [ ] Bundle all required dependencies
  - [ ] Platform-specific builds if needed
  - [ ] Version management and releases

- [ ] **Installation methods**
  - [ ] PyPI package: `pip install mcp-vibe-example`
  - [ ] Homebrew formula for easy installation
  - [ ] Pre-built executables for major platforms
  - [ ] Integration guides for MCP clients

#### Technical Architecture

```
┌─────────────────────────────────────────┐
│           mcp-vibe Process              │
│                                         │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │ Background      │ │ Main Thread     ││
│  │ Thread          │ │                 ││
│  │                 │ │ FastMCP Server  ││
│  │ gRPC Server     │ │ (stdio/MCP      ││
│  │ VibeService     │ │  protocol)      ││
│  │ (localhost:     │ │                 ││
│  │  50051)         │ │ Generated Tools ││
│  └─────────────────┘ └─────────────────┘│
│           │                   │          │
│           └─── in-process ────┘          │
└─────────────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    │   LLM Client      │
    │  (Claude Desktop) │
    │   MCP Protocol    │
    └───────────────────┘
```

#### Success Criteria
1. **Single command installation**: `pip install mcp-vibe-example` or `brew install mcp-vibe`
2. **Zero-config MCP integration**: Add to Claude Desktop with just `{"command": "mcp-vibe"}`
3. **Complete demo workflow**: LLM can set/get vibe through natural language
4. **Self-contained operation**: No external dependencies or separate gRPC server needed
5. **Development template**: Clear example for other gRPC services

#### Expected Deliverables
- [ ] `mcp_vibe_example/` Python package with integrated server
- [ ] `mcp-vibe` console script entry point
- [ ] `pyproject.toml` with proper packaging configuration
- [ ] Installation documentation and usage examples
- [ ] Integration guide for other gRPC services
- [ ] Example MCP client configuration

#### Benefits
- **Immediate demonstrable value** - Working end-to-end example in single process
- **Template for users** - Clear pattern for embedding gRPC in MCP applications
- **Distribution proof** - Shows the plugin generates production-ready code
- **Marketing asset** - Concrete demo that's easy to install and try
- **Testing platform** - Real-world validation of generated MCP tools

#### Implementation Notes
- **Threading model**: gRPC server runs in background thread, FastMCP in main thread
- **No external dependencies**: Everything embedded in single Python application
- **Based on generated code**: Uses `example_pb2_mcp.py` as foundation, with embedded gRPC server
- **Easy installation**: Standard Python packaging for distribution via PyPI/Homebrew

*This self-contained example will demonstrate how to embed gRPC services directly in MCP applications, providing a complete template for users.*