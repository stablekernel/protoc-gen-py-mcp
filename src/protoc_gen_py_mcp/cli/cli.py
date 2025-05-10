import sys
from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf import descriptor_pb2

def main():
    # Read input from stdin
    data = sys.stdin.buffer.read()

    # Parse input as CodeGeneratorRequest
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    # Prepare response
    response = plugin.CodeGeneratorResponse()
    for proto_file in request.proto_file:
        f = response.file.add()
        f.name = proto_file.name.replace(".proto", "_mcp_pb2_generated.py")
        f.content = f"# Generated from {proto_file.name}\n"

    # Write response to stdout
    sys.stdout.buffer.write(response.SerializeToString())
