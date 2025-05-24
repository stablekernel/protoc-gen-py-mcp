"""Integrated MCP-gRPC server application.

This module provides a self-contained application that runs both:
1. A gRPC server (VibeService) in a background thread
2. An MCP server (FastMCP) in the main thread

The MCP server exposes the gRPC service methods as MCP tools that LLM clients
can use through natural language.
"""

import asyncio
import atexit
import signal
import sys
import threading
import time
from concurrent import futures
from typing import Optional

import grpc
from fastmcp import FastMCP

# Import generated protobuf modules
from protos import example_pb2, example_pb2_grpc


class VibeService(example_pb2_grpc.VibeServiceServicer):
    """gRPC service implementation for managing server vibe."""

    def __init__(self):
        self.current_vibe = "neutral"
        self._lock = threading.Lock()

    def SetVibe(self, request, context):
        """Set the server's vibe."""
        with self._lock:
            prev = self.current_vibe
            self.current_vibe = request.vibe
            print(f"[gRPC] Vibe changed from '{prev}' to '{self.current_vibe}'")
            return example_pb2.SetVibeResponse(
                previous_vibe=prev, vibe=self.current_vibe
            )

    def GetVibe(self, request, context):
        """Get the current server vibe."""
        with self._lock:
            print(f"[gRPC] Vibe requested, returning '{self.current_vibe}'")
            return example_pb2.GetVibeResponse(vibe=self.current_vibe)


class IntegratedVibeServer:
    """Integrated server that runs both gRPC and MCP servers."""

    def __init__(self, grpc_port: int = 50051, debug: bool = False):
        self.grpc_port = grpc_port
        self.debug = debug
        self.grpc_server: Optional[grpc.Server] = None
        self.grpc_thread: Optional[threading.Thread] = None
        self.mcp = FastMCP("MCP Vibe Server")
        self._setup_mcp_tools()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def shutdown_handler(signum, frame):
            print(f"[Main] Received signal {signum}, shutting down...")
            self.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        atexit.register(self.shutdown)

    def _setup_mcp_tools(self):
        """Setup MCP tools that connect to the embedded gRPC server."""

        @self.mcp.tool(name="SetVibe", description="Set the server's vibe")
        def set_vibe(vibe: str) -> dict:
            """Set the vibe of the server.

            Args:
                vibe: The new vibe to set (e.g., 'happy', 'excited', 'calm')

            Returns:
                Dictionary with previous and current vibe
            """
            try:
                # Connect to embedded gRPC server
                channel = grpc.insecure_channel(f"localhost:{self.grpc_port}")
                stub = example_pb2_grpc.VibeServiceStub(channel)

                # Create request and call gRPC service
                request = example_pb2.SetVibeRequest(vibe=vibe)
                response = stub.SetVibe(request)

                result = {
                    "previous_vibe": response.previous_vibe,
                    "current_vibe": response.vibe,
                    "success": True,
                }

                if self.debug:
                    print(f"[MCP] SetVibe result: {result}")

                return result

            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e),
                    "type": type(e).__name__,
                }
                print(f"[MCP] SetVibe error: {error_result}")
                return error_result
            finally:
                try:
                    channel.close()
                except:
                    pass

        @self.mcp.tool(name="GetVibe", description="Get the current server vibe")
        def get_vibe() -> dict:
            """Get the current vibe of the server.

            Returns:
                Dictionary with the current vibe
            """
            try:
                # Connect to embedded gRPC server
                channel = grpc.insecure_channel(f"localhost:{self.grpc_port}")
                stub = example_pb2_grpc.VibeServiceStub(channel)

                # Create request and call gRPC service
                request = example_pb2.GetVibeRequest()
                response = stub.GetVibe(request)

                result = {
                    "current_vibe": response.vibe,
                    "success": True,
                }

                if self.debug:
                    print(f"[MCP] GetVibe result: {result}")

                return result

            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e),
                    "type": type(e).__name__,
                }
                print(f"[MCP] GetVibe error: {error_result}")
                return error_result
            finally:
                try:
                    channel.close()
                except:
                    pass

    def _start_grpc_server(self):
        """Start the gRPC server in a background thread."""
        try:
            # Create gRPC server
            self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            example_pb2_grpc.add_VibeServiceServicer_to_server(
                VibeService(), self.grpc_server
            )
            self.grpc_server.add_insecure_port(f"[::]:{self.grpc_port}")
            
            # Start server
            self.grpc_server.start()
            print(f"[gRPC] VibeService server started on port {self.grpc_port}")

            # Keep the server running
            try:
                while True:
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                pass

        except Exception as e:
            print(f"[gRPC] Failed to start server: {e}")
            raise

    def start_grpc_server(self):
        """Start the gRPC server in a background thread."""
        self.grpc_thread = threading.Thread(
            target=self._start_grpc_server, daemon=True, name="gRPC-Server"
        )
        self.grpc_thread.start()

        # Wait a moment for server to start
        time.sleep(0.5)

        # Verify server is running
        max_retries = 10
        for i in range(max_retries):
            try:
                channel = grpc.insecure_channel(f"localhost:{self.grpc_port}")
                stub = example_pb2_grpc.VibeServiceStub(channel)
                request = example_pb2.GetVibeRequest()
                response = stub.GetVibe(request)
                channel.close()
                print(f"[gRPC] Server verified running (initial vibe: {response.vibe})")
                break
            except Exception as e:
                if i == max_retries - 1:
                    raise RuntimeError(f"gRPC server failed to start after {max_retries} retries: {e}")
                time.sleep(0.1)

    def start_mcp_server(self):
        """Start the MCP server (blocking call)."""
        print("[MCP] Starting MCP server...")
        try:
            self.mcp.run()
        except (KeyboardInterrupt, SystemExit):
            print("[MCP] MCP server stopped")

    def shutdown(self):
        """Shutdown both servers gracefully."""
        if self.grpc_server:
            print("[gRPC] Shutting down gRPC server...")
            self.grpc_server.stop(grace=5)
            self.grpc_server = None

    def run(self):
        """Run the integrated server (start gRPC in background, MCP in foreground)."""
        try:
            print("[Main] Starting integrated MCP-gRPC server...")
            
            # Start gRPC server in background
            self.start_grpc_server()
            
            # Start MCP server in foreground (this will block)
            self.start_mcp_server()
            
        except Exception as e:
            print(f"[Main] Error running server: {e}")
            raise
        finally:
            self.shutdown()


def main():
    """Main entry point for the mcp-vibe application."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Vibe Server - gRPC service exposed as MCP tools"
    )
    parser.add_argument(
        "--port", type=int, default=50051, help="gRPC server port (default: 50051)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug output"
    )
    
    args = parser.parse_args()

    try:
        server = IntegratedVibeServer(grpc_port=args.port, debug=args.debug)
        server.run()
    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user")
    except Exception as e:
        print(f"[Main] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()