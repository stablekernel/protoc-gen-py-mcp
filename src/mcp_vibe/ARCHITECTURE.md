# MCP Vibe Example Architecture

This document explains the technical architecture of the MCP Vibe Example application.

## Overview

The MCP Vibe Example demonstrates how to create a self-contained application that bridges gRPC services with MCP (Model Context Protocol) clients like LLMs. It runs both a gRPC server and an MCP server in a single process.

## Architecture Diagram

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

## Component Details

### 1. gRPC Server (Background Thread)

**File**: `mcp_vibe_app/server.py` - `VibeService` class

**Purpose**: Implements the actual business logic for managing server "vibe" state.

**Key Features**:
- Thread-safe vibe state management
- Standard gRPC service implementation
- Runs on localhost:50051 by default
- Automatic startup verification and retry logic

**Methods**:
- `SetVibe(SetVibeRequest) -> SetVibeResponse`
- `GetVibe(GetVibeRequest) -> GetVibeResponse`

### 2. MCP Server (Main Thread)

**File**: `mcp_vibe_app/server.py` - `IntegratedVibeServer._setup_mcp_tools()`

**Purpose**: Exposes gRPC service methods as MCP tools that LLMs can call.

**Key Features**:
- FastMCP-based tool registration
- JSON-serialized responses for LLM consumption
- Robust error handling and logging
- Automatic gRPC client connection management

**Tools**:
- `SetVibe`: Calls gRPC SetVibe and returns structured result
- `GetVibe`: Calls gRPC GetVibe and returns current state

### 3. Integration Layer

**File**: `mcp_vibe_app/server.py` - `IntegratedVibeServer` class

**Purpose**: Orchestrates both servers and manages their lifecycle.

**Key Features**:
- Threading coordination between gRPC and MCP servers
- Graceful shutdown handling
- Signal handling for clean termination
- Configuration management (ports, debug mode)
- Startup verification with retry logic

## Data Flow

### Typical Interaction Flow

1. **Startup**:
   ```
   User runs: mcp-vibe
   → IntegratedVibeServer.run()
   → Start gRPC server in background thread
   → Start MCP server in main thread (blocks)
   ```

2. **LLM Tool Call**:
   ```
   LLM Client → MCP Protocol → FastMCP Server
   → MCP Tool Function → gRPC Client Call
   → gRPC Server → Business Logic → Response
   → gRPC Client ← gRPC Server
   → MCP Tool ← gRPC Client (JSON serialization)
   → FastMCP Server ← MCP Tool
   → MCP Protocol ← FastMCP Server
   → LLM Client ← MCP Protocol
   ```

3. **Shutdown**:
   ```
   SIGINT/SIGTERM → Signal Handler
   → server.shutdown() → Stop gRPC server
   → Exit MCP server loop → Clean termination
   ```

## Design Patterns

### 1. Embedded Service Pattern

Instead of connecting to an external gRPC server, this example embeds the gRPC server directly in the application. This provides:

- **Self-contained operation**: No external dependencies
- **Simplified deployment**: Single executable
- **Consistent state**: Shared process memory
- **Easy development**: Everything in one codebase

### 2. Thread Separation

The gRPC server runs in a background thread while the MCP server runs in the main thread. This provides:

- **Non-blocking operation**: MCP protocol handled independently
- **Resource isolation**: gRPC thread pool separate from MCP handling
- **Clean shutdown**: Main thread can coordinate cleanup

### 3. Tool Bridge Pattern

MCP tools act as bridges between the MCP protocol and gRPC services:

```python
@mcp.tool(name="SetVibe", description="Set the server's vibe")
def set_vibe(vibe: str) -> dict:
    # Bridge: MCP tool → gRPC call → JSON response
    channel = grpc.insecure_channel(f"localhost:{self.grpc_port}")
    stub = VibeServiceStub(channel)
    response = stub.SetVibe(SetVibeRequest(vibe=vibe))
    return {"previous_vibe": response.previous_vibe, ...}
```

## Configuration

### Command Line Options

- `--port PORT`: gRPC server port (default: 50051)
- `--debug`: Enable verbose logging
- `--help`: Show usage information

### Environment Variables

None currently, but could be extended for:
- Authentication configuration
- Service discovery settings
- Logging configuration

## Error Handling

### gRPC Server Errors

- Connection failures during startup
- Port already in use
- Service implementation exceptions

### MCP Tool Errors

- gRPC connection failures
- Request/response serialization errors
- Tool parameter validation

### Integration Errors

- Thread coordination issues
- Shutdown sequence problems
- Signal handling edge cases

## Extension Points

### Adding New Tools

1. Add new RPC method to `.proto` file
2. Implement method in `VibeService` class
3. Add corresponding MCP tool in `_setup_mcp_tools()`
4. Update documentation and tests

### Configuration Enhancement

1. Add new command line arguments
2. Update `IntegratedVibeServer.__init__()`
3. Pass configuration to relevant components
4. Document new options

### Authentication

1. Add auth configuration options
2. Configure gRPC server with credentials
3. Update MCP tools to use authenticated channels
4. Handle auth errors appropriately

## Performance Considerations

### Threading Model

- Single gRPC server thread pool (configurable)
- Single MCP server thread (FastMCP handles async internally)
- Minimal lock contention (only in VibeService state)

### Resource Usage

- Memory: Minimal overhead for embedded approach
- CPU: Dominated by protobuf serialization/deserialization
- Network: Only localhost loopback for gRPC calls

### Scalability

Current design is suitable for:
- Single-user development/testing
- Prototype demonstrations
- Small-scale personal automation

For production scale:
- Consider external gRPC server deployment
- Add connection pooling
- Implement proper authentication
- Add monitoring and metrics

## Testing Strategy

### Unit Tests

- Individual component testing (gRPC service, MCP tools)
- Mock-based testing for integration points
- Error condition testing

### Integration Tests

- Full startup/shutdown cycle testing
- End-to-end tool call testing
- Error propagation testing

### Manual Testing

- Demo script for interactive testing
- MCP client integration testing
- Performance and resource usage testing

This architecture provides a solid foundation for bridging gRPC services with MCP clients while maintaining simplicity and extensibility.