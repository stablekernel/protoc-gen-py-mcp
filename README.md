# protoc-gen-py-mcp

A [Protocol Buffer](https://protobuf.dev/) compiler plugin that generates [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) servers from gRPC service definitions. This enables AI models to interact with existing [gRPC](https://grpc.io/) services using natural language, bridging the gap between AI capabilities and protocol buffer-based codebases.

**⚡ Key Features:**
- **Zero-config generation**: Automatically creates MCP tools from gRPC service methods
- **Async/await support**: Modern Python patterns for high-performance applications
- **Comprehensive authentication**: Bearer tokens, API keys, mTLS, and custom auth
- **Package-aware structure**: Follows protobuf conventions for clean organization
- **Extensive customization**: 20+ configuration options for naming, auth, and behavior
- **Production-ready**: Type hints, error handling, and comprehensive testing

## Quick Start

### Prerequisites

- **Python 3.10+**
- **protoc 3.20+** - [Installation guide](https://grpc.io/docs/protoc-installation/)
- **uv** (recommended) or pip for dependency management

### Installation

```bash
# Install the plugin
pip install protoc-gen-py-mcp

# Or with uv (recommended)
uv add protoc-gen-py-mcp
```

### Basic Usage

1. **Create a proto file** (`example.proto`):

```protobuf
syntax = "proto3";

package example.v1;

service GreeterService {
  // Say hello to someone
  rpc SayHello(HelloRequest) returns (HelloResponse) {}
}

message HelloRequest {
  string name = 1;
}

message HelloResponse {
  string message = 1;
}
```

2. **Generate MCP server code**:

```bash
# Generate standard protobuf files + MCP server
protoc --python_out=gen --grpc_python_out=gen --pyi_out=gen \
       --py-mcp_out=gen \
       example.proto
```

3. **Use the generated MCP server**:

```python
from gen.example.v1.example_pb2_mcp import create_greeter_service_server

# Create MCP server with gRPC connection
mcp_server = create_greeter_service_server()

# Add to your MCP application
if __name__ == "__main__":
    mcp_server.run()
```

That's it! Your gRPC service is now accessible via MCP protocol.

## Configuration Options

The plugin supports extensive customization via command-line parameters:

```bash
# Production API setup with authentication
protoc --py-mcp_out=gen \
  --py-mcp_opt="grpc_target=api.prod.com:443,auth_type=bearer,async=true,timeout=60" \
  api.proto

# Development with debug output  
protoc --py-mcp_out=gen \
  --py-mcp_opt="debug=verbose,insecure=true,grpc_target=localhost:9090" \
  service.proto

# Custom naming and output
protoc --py-mcp_out=servers \
  --py-mcp_opt="output_suffix=_server.py,tool_name_case=camel,server_name_pattern={service}MCP" \
  services.proto
```

**📖 See [PLUGIN_PARAMETERS.md](PLUGIN_PARAMETERS.md) for complete documentation of all 20+ configuration options.**

## Authentication Examples

### Bearer Token Authentication
```bash
protoc --py-mcp_out=gen \
  --py-mcp_opt="auth_type=bearer,grpc_target=secure-api.com:443" \
  secure.proto
```

### API Key Authentication  
```bash
protoc --py-mcp_out=gen \
  --py-mcp_opt="auth_type=api_key,auth_header=X-API-Key,grpc_target=api.example.com" \
  api.proto
```

### Mutual TLS
```bash
protoc --py-mcp_out=gen \
  --py-mcp_opt="auth_type=mtls,grpc_target=mtls-api.internal:443" \
  internal.proto
```

## Project Structure

The plugin follows protobuf package conventions:

```
your-project/
├── protos/
│   └── example/v1/
│       └── service.proto      # package example.v1;
├── gen/
│   └── example/v1/            # Generated code follows package structure
│       ├── __init__.py
│       ├── service_pb2.py     # Standard protobuf
│       ├── service_pb2_grpc.py # gRPC stubs  
│       └── service_pb2_mcp.py # MCP server (this plugin)
└── main.py
```

## Integration with Build Systems

### Makefile Integration
```makefile
PROTO_SRC = protos/example/v1/service.proto
GEN_DIR = gen

.PHONY: generate clean

generate:
	protoc -I=protos \
		--python_out=$(GEN_DIR) \
		--grpc_python_out=$(GEN_DIR) \
		--pyi_out=$(GEN_DIR) \
		--py-mcp_out=$(GEN_DIR) \
		$(PROTO_SRC)

clean:
	find $(GEN_DIR) -name "*_pb2*.py" -delete
```

### CI/CD Integration
```yaml
# .github/workflows/generate.yml
- name: Generate MCP servers
  run: |
    pip install protoc-gen-py-mcp
    make generate
    
- name: Test generated code
  run: |
    python -c "from gen.example.v1.service_pb2_mcp import create_service_server"
```

## Complete Working Example: MCP Vibe Server

The repository includes a **complete, working example** that demonstrates the full plugin workflow from proto definition to working MCP server.

### 📁 Example Location: `src/mcp_vibe/`

This directory contains a **production-ready reference implementation** showing:

- **Embedded gRPC service** - Full `VibeService` implementation
- **Generated MCP tools** - Created automatically by protoc-gen-py-mcp  
- **Integrated server** - Both gRPC and MCP servers in one process
- **Claude Desktop integration** - Verified working configuration
- **Complete packaging** - Installable Python package with CLI

### 🚀 Architecture Overview

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
│  │  50051)         │ │ MCP Tools:      ││
│  │                 │ │ - SetVibe       ││
│  │                 │ │ - GetVibe       ││
│  └─────────────────┘ └─────────────────┘│
│           │                   │          │
│           └─── localhost ─────┘          │
└─────────────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    │   LLM Client      │
    │  (Claude Desktop) │
    │   MCP Protocol    │
    └───────────────────┘
```

### 🎯 Key Demonstration Points

1. **Plugin Code Generation**: Shows exactly how protoc-gen-py-mcp transforms `.proto` files into working MCP tools
2. **Embedded Pattern**: Demonstrates running gRPC server and MCP server in single process
3. **Real-world Integration**: Provides template for production gRPC-to-MCP bridges  
4. **End-to-End Testing**: Includes integration tests and demo scripts

### 📖 Documentation

- **`src/mcp_vibe/README.md`** - Complete usage and installation guide
- **`src/mcp_vibe/ARCHITECTURE.md`** - Technical architecture deep-dive
- **`src/mcp_vibe/demo.py`** - Interactive testing script

### 🛠 Quick Start

```bash
# 1. Generate the MCP tools from proto definition
make proto

# 2. Install the example application
cd src/mcp_vibe
pip install -e .

# 3. Run the integrated server
mcp-vibe --debug

# 4. Test with Claude Desktop (see README for config)
```

**✅ VERIFIED**: This example has been tested and confirmed working with Claude Desktop!

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vibe-example": {
      "command": "mcp-vibe"
    }
  }
}
```

You can then ask Claude: *"Set the vibe to excited"* or *"What's the current vibe?"*

## Advanced Features

### Async/Await Support
```bash
# Generate async MCP tools
protoc --py-mcp_out=gen --py-mcp_opt="async=true" service.proto
```

### Streaming RPC Handling
```bash
# Configure streaming behavior
protoc --py-mcp_out=gen --py-mcp_opt="stream_mode=collect" streaming.proto
```

### Custom Error Handling
```bash
# Detailed error responses
protoc --py-mcp_out=gen --py-mcp_opt="error_format=detailed" service.proto
```

### Debug and Development
```bash
# Full debug output with generated code
protoc --py-mcp_out=gen \
  --py-mcp_opt="debug=trace,show_generated=true,show_types=true" \
  service.proto
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/your-org/protoc-gen-py-mcp
cd protoc-gen-py-mcp
uv venv && source .venv/bin/activate
uv pip install -e .

# Run tests
make test

# Quality checks
make check-all
```

## Testing

```bash
# Run all tests
make test

# Integration tests
make test-integration
```

## Troubleshooting

### Common Issues

**Plugin not found:**
```bash
# Ensure plugin is in PATH
which protoc-gen-py-mcp
# Or specify full path
protoc --plugin=protoc-gen-py-mcp=/path/to/plugin ...
```

**Import errors in generated code:**
```bash
# Ensure proper Python package structure
# Generated code should have __init__.py files
ls gen/example/v1/__init__.py
```

**gRPC connection issues:**
```bash
# Test with insecure channel for development
protoc --py-mcp_opt="insecure=true,debug=basic" service.proto
```

### Debug Mode

Enable debug output for troubleshooting:

```bash
protoc --py-mcp_opt="debug=trace,show_generated=true" service.proto
```

## Limitations

- **Streaming RPCs**: Currently collected into lists (configurable via `stream_mode`)
- **Complex nested types**: Basic support for deeply nested oneofs
- **Custom options**: Proto custom options not yet supported

## Roadmap

- [ ] Streaming RPC native support
- [ ] Custom proto option handling
- [ ] Template customization system
- [ ] Performance optimizations
- [ ] IDE integration

## Support

- **Documentation**: [Plugin Parameters](PLUGIN_PARAMETERS.md) | [Contributing](CONTRIBUTING.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/protoc-gen-py-mcp/issues)
- **Examples**: See `examples/` directory

## About Topeka

[Topeka](https://topeka.ai) is an open source project providing code generators for [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction). It facilitates seamless MCP integration with existing gRPC applications through protoc compiler plugins.

**Semantic Versioning**: Plugins follow [SemVer](https://semver.org/). Pre-1.0.0 releases may include breaking changes to generated servers, while maintaining plugin compatibility.

## Maintainers

**[Stable Kernel](https://stablekernel.com)** is the primary maintainer and sponsor of this project. We're a digital transformation company building LLM-enabled solutions for growing businesses.

Our custom software development and technology services are trusted by Fortune 500 companies worldwide. Every day, millions of people rely on software we've developed.

## License

[Apache License 2.0](LICENSE) - See LICENSE file for details.