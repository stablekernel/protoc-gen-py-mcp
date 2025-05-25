#!/usr/bin/env python3
"""Demo script showing the MCP Vibe Example in action.

This script demonstrates how the MCP tools interact with the embedded gRPC server.
"""

import json
import sys
from pathlib import Path

from mcp_vibe_app.server import IntegratedVibeServer

# Add the examples/gen directory to the Python path so we can import generated code
examples_gen = Path(__file__).parent.parent.parent / "examples" / "gen"
sys.path.insert(0, str(examples_gen))


def demo_mcp_tools():
    """Demonstrate the MCP tools functionality."""
    print("🚀 MCP Vibe Example Demo")
    print("=" * 40)

    # Start the integrated server
    server = IntegratedVibeServer(debug=False)
    server.start_grpc_server()
    print("✅ Started integrated gRPC + MCP server")

    try:
        # Simulate MCP tool calls like an LLM would make them
        print("\n📡 Simulating LLM interactions via MCP tools...\n")

        # Demo 1: Get initial vibe
        print("🤖 LLM: 'What's the current vibe?'")
        print("🔧 Calling GetVibe tool...")

        # Access the tool function through the MCP server's registered tools
        # Note: In real usage, this would be called via MCP protocol
        get_vibe_result = None
        set_vibe_result = None

        # We need to call the actual tool functions
        # Let's call them through gRPC to simulate the MCP tool behavior
        import grpc
        from example.v1 import example_pb2, example_pb2_grpc  # noqa: E402

        channel = grpc.insecure_channel("localhost:50051")
        stub = example_pb2_grpc.VibeServiceStub(channel)

        # Simulate GetVibe tool
        response = stub.GetVibe(example_pb2.GetVibeRequest())
        get_vibe_result = {"current_vibe": response.vibe, "success": True}
        print(f"📋 Result: {json.dumps(get_vibe_result, indent=2)}")
        print(f"💬 LLM: 'The server is currently feeling {get_vibe_result['current_vibe']}'")

        print("\n" + "-" * 40 + "\n")

        # Demo 2: Set a new vibe
        print("🤖 LLM: 'Set the server vibe to excited'")
        print("🔧 Calling SetVibe tool with vibe='excited'...")

        response = stub.SetVibe(example_pb2.SetVibeRequest(vibe="excited"))
        set_vibe_result = {
            "previous_vibe": response.previous_vibe,
            "current_vibe": response.vibe,
            "success": True,
        }
        print(f"📋 Result: {json.dumps(set_vibe_result, indent=2)}")
        print(
            f"💬 LLM: 'Changed the vibe from {set_vibe_result['previous_vibe']} to {set_vibe_result['current_vibe']}'"
        )

        print("\n" + "-" * 40 + "\n")

        # Demo 3: Confirm the change
        print("🤖 LLM: 'What's the vibe now?'")
        print("🔧 Calling GetVibe tool again...")

        response = stub.GetVibe(example_pb2.GetVibeRequest())
        final_result = {"current_vibe": response.vibe, "success": True}
        print(f"📋 Result: {json.dumps(final_result, indent=2)}")
        print(f"💬 LLM: 'The server is now feeling {final_result['current_vibe']}!'")

        channel.close()

        print("\n" + "=" * 40)
        print("🎉 Demo completed successfully!")
        print("\n📝 What happened:")
        print("1. Started embedded gRPC server (VibeService)")
        print("2. MCP tools connected to the gRPC server internally")
        print("3. LLM interacted with gRPC service through natural language")
        print("4. State was maintained across tool calls")

        print("\n🔗 To connect with Claude Desktop:")
        print('Add this to your MCP settings: {"command": "mcp-vibe"}')

    finally:
        server.shutdown()
        print("\n✅ Server shut down cleanly")


if __name__ == "__main__":
    demo_mcp_tools()
