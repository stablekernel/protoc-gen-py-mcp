#!/usr/bin/env python3
"""Integration test for the MCP Vibe Example application."""

import sys
from pathlib import Path

from mcp_vibe_app.server import IntegratedVibeServer

# Add the examples/gen directory to the Python path so we can import generated code
examples_gen = Path(__file__).parent.parent.parent / "examples" / "gen"
sys.path.insert(0, str(examples_gen))


def test_server_integration():
    """Test that the integrated server works correctly."""
    print("Starting integration test...")

    try:
        # Create server instance
        server = IntegratedVibeServer(debug=True)

        # Start gRPC server
        server.start_grpc_server()
        print("✅ gRPC server started successfully")

        # Test direct gRPC calls to verify the service works
        import grpc
        from example.v1 import example_pb2, example_pb2_grpc  # noqa: E402

        channel = grpc.insecure_channel("localhost:50051")
        stub = example_pb2_grpc.VibeServiceStub(channel)

        # Test GetVibe
        response = stub.GetVibe(example_pb2.GetVibeRequest())
        print(f"✅ GetVibe works: {response.vibe}")

        # Test SetVibe
        response = stub.SetVibe(example_pb2.SetVibeRequest(vibe="excited"))
        print(f"✅ SetVibe works: {response.previous_vibe} -> {response.vibe}")

        # Test GetVibe again
        response = stub.GetVibe(example_pb2.GetVibeRequest())
        print(f"✅ State persisted: {response.vibe}")

        channel.close()

        # Test that MCP tools can be imported
        from example.v1.example_pb2_mcp import mcp  # noqa: E402

        print(f"✅ MCP server available with name: {mcp.name}")

        # Clean shutdown
        server.shutdown()
        print("✅ Server shutdown successful")

        print("\n🎉 All integration tests passed!")
        print("\nTo test with an MCP client:")
        print("1. Run: mcp-vibe")
        print('2. Add to Claude Desktop: {"command": "mcp-vibe"}')
        print("3. Ask Claude to 'set the vibe to happy' or 'what's the current vibe?'")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_server_integration()
    sys.exit(0 if success else 1)
