"""Integrated MCP-gRPC server application.

This module provides a self-contained application that runs both:
1. A gRPC server (VibeService) in a background thread
2. The generated MCP server (from protoc-gen-py-mcp) in the main thread

This demonstrates how the protoc-gen-py-mcp plugin automatically generates
MCP tools from gRPC service definitions, providing a complete working example.
"""

import atexit
import signal
import sys
import threading
import time
from concurrent import futures
from pathlib import Path
from typing import Optional

import grpc

# Add the examples/gen directory to the Python path so we can import generated code
examples_gen = Path(__file__).parent.parent.parent.parent / "examples" / "gen"
sys.path.insert(0, str(examples_gen))

# Import generated protobuf modules
# Note: These imports may show as unresolved in IDEs but work at runtime
from example.v1 import example_pb2, example_pb2_grpc  # noqa: E402


class VibeService(example_pb2_grpc.VibeServiceServicer):
    """gRPC service implementation for managing server vibe."""

    def __init__(self):
        self.current_vibe = "neutral"
        print(f"[gRPC] VibeService initialized with vibe: {self.current_vibe}")

    def SetVibe(self, request, context):
        """Set the server's vibe."""
        previous_vibe = self.current_vibe
        self.current_vibe = request.vibe

        print(f"[gRPC] SetVibe: '{previous_vibe}' -> '{self.current_vibe}'")

        return example_pb2.SetVibeResponse(previous_vibe=previous_vibe, vibe=self.current_vibe)

    def GetVibe(self, request, context):
        """Get the current server vibe."""
        print(f"[gRPC] GetVibe: returning '{self.current_vibe}'")

        return example_pb2.GetVibeResponse(vibe=self.current_vibe)


class IntegratedVibeServer:
    """Integrated server that runs both gRPC and MCP servers."""

    def __init__(self, grpc_port: int = 50051, debug: bool = False):
        self.grpc_port = grpc_port
        self.debug = debug
        self.grpc_server: Optional[grpc.Server] = None
        self.grpc_thread: Optional[threading.Thread] = None
        self.shutdown_requested = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self.shutdown)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"[Server] Received signal {signum}, shutting down...")
        self.shutdown()

    def start_grpc_server(self):
        """Start the gRPC server in a background thread."""

        def run_grpc():
            try:
                # Create gRPC server
                self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

                # Add the VibeService
                vibe_service = VibeService()
                example_pb2_grpc.add_VibeServiceServicer_to_server(vibe_service, self.grpc_server)

                # Add insecure port
                listen_addr = f"[::]:{self.grpc_port}"
                self.grpc_server.add_insecure_port(listen_addr)

                # Start the server
                self.grpc_server.start()
                print(f"[gRPC] Server started on port {self.grpc_port}")

                # Wait for termination
                self.grpc_server.wait_for_termination()
                print("[gRPC] Server terminated")

            except Exception as e:
                print(f"[gRPC] Server error: {e}")
                if self.debug:
                    import traceback

                    traceback.print_exc()

        # Start gRPC server in background thread
        self.grpc_thread = threading.Thread(target=run_grpc, daemon=True)
        self.grpc_thread.start()

        # Wait a moment for gRPC server to start
        time.sleep(0.5)
        print("[Server] gRPC server started in background thread")

    def start_mcp_server(self):
        """Start the generated MCP server in the main thread."""
        try:
            print("[Server] Starting generated MCP server...")
            print("[Server] The MCP tools were auto-generated from the proto file!")

            # Import the generated MCP module
            from example.v1.example_pb2_mcp import mcp  # noqa: E402

            # Run the generated MCP server
            # Note: The MCP server name is set in the generated code
            mcp.run()

        except Exception as e:
            print(f"[MCP] Server error: {e}")
            if self.debug:
                import traceback

                traceback.print_exc()

    def shutdown(self):
        """Shutdown both servers gracefully."""
        if self.shutdown_requested:
            return

        self.shutdown_requested = True
        print("[Server] Shutting down...")

        # Stop gRPC server
        if self.grpc_server:
            print("[Server] Stopping gRPC server...")
            self.grpc_server.stop(grace=2.0)

        # Wait for gRPC thread to finish
        if self.grpc_thread and self.grpc_thread.is_alive():
            self.grpc_thread.join(timeout=3.0)

        print("[Server] Shutdown complete")

    def run(self):
        """Run the integrated server."""
        print("[Server] Starting integrated MCP-gRPC server...")
        print(f"[Server] gRPC server will run on port {self.grpc_port}")
        print("[Server] MCP server will run on stdio")
        print()

        try:
            # Start gRPC server in background
            self.start_grpc_server()

            # Start MCP server in main thread (this blocks)
            self.start_mcp_server()

        except KeyboardInterrupt:
            print("\n[Server] Keyboard interrupt received")
        except Exception as e:
            print(f"[Server] Unexpected error: {e}")
            if self.debug:
                import traceback

                traceback.print_exc()
        finally:
            self.shutdown()


def main():
    """Main entry point for the mcp-vibe application."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Vibe Server - Generated from Proto")
    parser.add_argument("--port", type=int, default=50051, help="gRPC server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    print("=" * 60)
    print("MCP Vibe Server - Demonstrating protoc-gen-py-mcp")
    print("=" * 60)
    print("This example shows how the protoc-gen-py-mcp plugin")
    print("automatically generates MCP tools from gRPC services!")
    print()
    print("Try asking Claude:")
    print('  - "Set the vibe to excited"')
    print('  - "What\'s the current vibe?"')
    print('  - "Change the vibe to calm"')
    print("=" * 60)
    print()

    # Create and run the integrated server
    server = IntegratedVibeServer(grpc_port=args.port, debug=args.debug)
    server.run()


if __name__ == "__main__":
    main()
