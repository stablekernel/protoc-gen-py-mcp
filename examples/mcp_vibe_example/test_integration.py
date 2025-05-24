#!/usr/bin/env python3
"""Integration test for the MCP Vibe Example application."""

import threading
import time
import sys
from mcp_vibe_app.server import IntegratedVibeServer


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
        from protos import example_pb2, example_pb2_grpc
        
        channel = grpc.insecure_channel('localhost:50051')
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
        
        # Test that MCP tools are registered
        mcp_instance = server.mcp
        print(f"✅ MCP server created with name: {mcp_instance.name}")
        
        # Clean shutdown
        server.shutdown()
        print("✅ Server shutdown successful")
        
        print("\n🎉 All integration tests passed!")
        print("\nTo test with an MCP client:")
        print("1. Run: mcp-vibe")
        print("2. Add to Claude Desktop: {\"command\": \"mcp-vibe\"}")
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