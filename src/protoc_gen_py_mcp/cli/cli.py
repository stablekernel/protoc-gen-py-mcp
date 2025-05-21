import sys
from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf import descriptor_pb2

# Suffix for generated Python MCP files
_OUTPUT_FILE_SUFFIX = "_pb2_mcp.py"

def main() -> None:
    """
    Protoc plugin entry point.

    Reads a CodeGeneratorRequest from stdin, generates Python MCP server stubs,
    and writes a CodeGeneratorResponse to stdout.
    """
    # Read input from stdin
    data: bytes = sys.stdin.buffer.read()

    # Parse input as CodeGeneratorRequest
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    # Prepare response
    response = plugin.CodeGeneratorResponse()

    # Supported features (optional, but good practice)
    response.supported_features = plugin.CodeGeneratorResponse.Feature.FEATURE_PROTO3_OPTIONAL

    for proto_file in request.proto_file:
        # Ensure we have a FileDescriptorProto object, for type safety, though iterating
        # request.proto_file should yield these directly.
        if not isinstance(proto_file, descriptor_pb2.FileDescriptorProto):
            # This case should ideally not happen if protoc behaves correctly
            sys.stderr.write(f"Warning: Skipping non-FileDescriptorProto item: {type(proto_file)}\n")
            continue

        output_filename = proto_file.name.replace(".proto", _OUTPUT_FILE_SUFFIX)

        # Basic content generation
        # TODO: Implement actual MCP server stub generation logic here
        content = f"# Generated from {proto_file.name}\n"
        content += f"# Output to: {output_filename}\n\n"
        content += f"from fastmcp import FastMCP\n\n"
        content += f"mcp = FastMCP(\"MCP Server from Proto\")\n\n"
        # content += f"class {proto_file.name.replace('.proto', '')}Server(FastMCP):\n"
        # content += f"    def __init__(self):\n"
        # content += f"        super().__init__()\n"
        # content += f"        self.register_service({proto_file.name.replace('.proto', '')}Service)\n"
        content += f"print(\"MCP Python stub generated\")\n\n"

        content += f"if __name__ == \"__main__\":\n"
        content += f"    mcp.run()\n\n"


        f = response.file.add()
        f.name = output_filename
        f.content = content

    # Write response to stdout
    sys.stdout.buffer.write(response.SerializeToString())
