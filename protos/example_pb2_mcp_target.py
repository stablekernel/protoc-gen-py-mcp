# Generated from protos/example.proto
# Output to: protos/example_pb2_mpc.py

from fastmcp import FastMCP
import grpc
from protos import example_pb2
from protos import example_pb2_grpc

print("MCP Python stub generated")

mcp = FastMCP("MCP Server from Proto")

@mcp.tool(name="SetVibe", description="Set the vibe")
def SetVibe(vibe: str):
    channel = grpc.insecure_channel('localhost:50051')
    stub = example_pb2_grpc.VibeServiceStub(channel)
    set_response = stub.SetVibe(example_pb2.SetVibeRequest(vibe=vibe))
    print(set_response)
    # return protos.exampleResponse()

@mcp.tool(name="GetVibe", description="Get the vibe")
def GetVibe():
    channel = grpc.insecure_channel('localhost:50051')
    stub = example_pb2_grpc.VibeServiceStub(channel)
    get_response = stub.GetVibe(example_pb2.GetVibeRequest())
    print(get_response)
    # return protos.exampleResponse()

# class protos/exampleServer(FastMCP):
#     def __init__(self):
#         super().__init__()
#         self.register_service(protos/exampleService)


if __name__ == "__main__":
    mcp.run()
