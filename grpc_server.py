import sys
import os
import grpc
from concurrent import futures
import time

# Add the examples/gen directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples', 'gen'))

from example.v1 import example_pb2
from example.v1 import example_pb2_grpc


class VibeService(example_pb2_grpc.VibeServiceServicer):
    """Implementation of the VibeService gRPC service."""
    
    def __init__(self):
        """Initialize the service with a default vibe."""
        self.current_vibe = "neutral"

    def SetVibe(self, request, context):
        """Set the current vibe of the server."""
        prev = self.current_vibe
        self.current_vibe = request.vibe
        print(f"Vibe changed from '{prev}' to '{self.current_vibe}'")
        return example_pb2.SetVibeResponse(previous_vibe=prev, vibe=self.current_vibe)

    def GetVibe(self, request, context):
        """Get the current vibe of the server."""
        print(f"Vibe requested, returning '{self.current_vibe}'")
        return example_pb2.GetVibeResponse(vibe=self.current_vibe)


def serve():
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    example_pb2_grpc.add_VibeServiceServicer_to_server(VibeService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("VibeService gRPC server started on port 50051.")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.stop(0)


if __name__ == '__main__':
    serve()