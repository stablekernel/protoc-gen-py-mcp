# Plugin Parameters Reference

Complete documentation for all configuration options available in protoc-gen-py-mcp.

## Usage

Parameters are passed to the plugin using the `--py-mcp_opt` flag:

```bash
protoc --py-mcp_out=. --py-mcp_opt="param1=value1,param2=value2" example.proto
```

## Core Configuration

### `debug`
**Type:** `string` | **Default:** `none`  
**Values:** `none`, `basic`, `verbose`, `trace`

Controls debug output level for plugin development and troubleshooting.

```bash
# Basic debug info
--py-mcp_opt="debug=basic"

# Verbose debug with detailed type information  
--py-mcp_opt="debug=verbose"

# Full trace with generated code output
--py-mcp_opt="debug=trace"
```

### `output_suffix`
**Type:** `string` | **Default:** `_pb2_mcp.py`

Custom suffix for generated MCP files.

```bash
# Generate files with custom suffix
--py-mcp_opt="output_suffix=_mcp_server.py"
# Result: example_mcp_server.py instead of example_pb2_mcp.py
```

## gRPC Connection

### `grpc_target`
**Type:** `string` | **Default:** `localhost:50051`

Target address for gRPC server connections in generated code.

```bash
--py-mcp_opt="grpc_target=api.example.com:443"
```

### `insecure`
**Type:** `boolean` | **Default:** `false`

Use insecure gRPC channels (no TLS).

```bash
# For development/testing
--py-mcp_opt="insecure=true"
```

### `timeout`
**Type:** `integer` | **Default:** `30`

gRPC call timeout in seconds.

```bash
--py-mcp_opt="timeout=60"
```

### `async`
**Type:** `boolean` | **Default:** `false`

Generate async/await tool functions instead of synchronous ones.

```bash
--py-mcp_opt="async=true"
```

## Code Generation Patterns

### `server_name_pattern`
**Type:** `string` | **Default:** `{service}`

Pattern for MCP server names. Use `{service}` placeholder.

```bash
--py-mcp_opt="server_name_pattern={service}MCPServer"
# VibeService -> VibeServiceMCPServer
```

### `function_name_pattern`
**Type:** `string` | **Default:** `create_{service}_server`

Pattern for server creation function names.

```bash
--py-mcp_opt="function_name_pattern=make_{service}_mcp"
# VibeService -> make_vibe_service_mcp()
```

### `tool_name_case`
**Type:** `string` | **Default:** `snake`  
**Values:** `snake`, `camel`, `pascal`, `kebab`

Case conversion for MCP tool names.

```bash
# snake_case (default)
--py-mcp_opt="tool_name_case=snake"
# GetUserInfo -> get_user_info

# camelCase  
--py-mcp_opt="tool_name_case=camel"
# GetUserInfo -> getUserInfo

# PascalCase
--py-mcp_opt="tool_name_case=pascal" 
# GetUserInfo -> GetUserInfo

# kebab-case
--py-mcp_opt="tool_name_case=kebab"
# GetUserInfo -> get-user-info
```

## Documentation & Comments

### `include_comments`
**Type:** `boolean` | **Default:** `true`

Include proto comments in generated MCP tool descriptions.

```bash
# Disable comment extraction
--py-mcp_opt="include_comments=false"
```

## Error Handling

### `error_format`
**Type:** `string` | **Default:** `standard`  
**Values:** `standard`, `simple`, `detailed`

Format for error responses in generated tools.

```bash
# Simple error messages
--py-mcp_opt="error_format=simple"

# Detailed error information
--py-mcp_opt="error_format=detailed"
```

### `stream_mode`
**Type:** `string` | **Default:** `collect`  
**Values:** `collect`, `skip`, `warn`

How to handle streaming RPC methods.

```bash
# Skip streaming methods entirely
--py-mcp_opt="stream_mode=skip"

# Generate warnings for streaming methods
--py-mcp_opt="stream_mode=warn"

# Collect streaming responses (default)
--py-mcp_opt="stream_mode=collect"
```

## Authentication

### `auth_type`
**Type:** `string` | **Default:** `none`  
**Values:** `none`, `bearer`, `api_key`, `mtls`, `custom`

Authentication mechanism for gRPC calls.

```bash
# Bearer token authentication
--py-mcp_opt="auth_type=bearer"

# API key authentication  
--py-mcp_opt="auth_type=api_key"

# Mutual TLS
--py-mcp_opt="auth_type=mtls"

# Custom authentication
--py-mcp_opt="auth_type=custom"
```

### `auth_header`
**Type:** `string` | **Default:** `Authorization`

Header name for API key or bearer token authentication.

```bash
--py-mcp_opt="auth_type=api_key,auth_header=X-API-Key"
```

### `auth_metadata`
**Type:** `boolean` | **Default:** `true`

Generate metadata injection code for authentication.

```bash
# Disable auth metadata generation
--py-mcp_opt="auth_metadata=false"
```

## Debug & Development

### `show_generated`
**Type:** `boolean` | **Default:** `false`

Show generated code content in debug output (requires debug mode).

```bash
--py-mcp_opt="debug=verbose,show_generated=true"
```

### `show_types`
**Type:** `boolean` | **Default:** `false`

Show detailed type information in debug output (requires debug mode).

```bash
--py-mcp_opt="debug=verbose,show_types=true"
```

## Complete Examples

### Basic Development Setup
```bash
protoc --py-mcp_out=gen \
  --py-mcp_opt="debug=basic,grpc_target=localhost:9090,insecure=true" \
  example.proto
```

### Production API Integration
```bash
protoc --py-mcp_out=src/generated \
  --py-mcp_opt="grpc_target=api.prod.com:443,auth_type=bearer,timeout=60,async=true" \
  api.proto
```

### Custom Naming and Output
```bash
protoc --py-mcp_out=mcp_servers \
  --py-mcp_opt="output_suffix=_server.py,server_name_pattern={service}MCPServer,tool_name_case=camel" \
  services.proto
```

### Debug and Troubleshooting
```bash
protoc --py-mcp_out=debug \
  --py-mcp_opt="debug=trace,show_generated=true,show_types=true,include_comments=true" \
  problem.proto
```

## Parameter Combinations

Multiple parameters are comma-separated:

```bash
--py-mcp_opt="async=true,auth_type=bearer,grpc_target=api.example.com:443,timeout=30,debug=basic"
```

## Boolean Parameter Formats

All these formats work for boolean parameters:
- `true`, `1`, `yes` → true
- `false`, `0`, `no` → false
- Omitted → default value

```bash
# All equivalent ways to enable async mode
--py-mcp_opt="async=true"
--py-mcp_opt="async=1" 
--py-mcp_opt="async=yes"
```