import grpc
from concurrent import futures
import time

from protos import example_pb2
from protos import example_pb2_grpc

class VibeService(example_pb2_grpc.VibeServiceServicer):
    def __init__(self):
        self.current_vibe = "neutral"

    def SetVibe(self, request, context):
        prev = self.current_vibe
        self.current_vibe = request.vibe
        print(f"Vibe changed from '{prev}' to '{self.current_vibe}'")
        return example_pb2.SetVibeResponse(previous_vibe=prev, vibe=self.current_vibe)

    def GetVibe(self, request, context):
        print(f"Vibe requested, returning '{self.current_vibe}'")
        return example_pb2.GetVibeResponse(vibe=self.current_vibe)

def serve():
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
