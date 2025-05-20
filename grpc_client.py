import grpc
from protos import example_pb2
from protos import example_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = example_pb2_grpc.VibeServiceStub(channel)

    # Set the vibe
    print("Setting vibe to 'mid'...")
    set_response = stub.SetVibe(example_pb2.SetVibeRequest(vibe='mid'))
    print(f"Previous vibe: {set_response.previous_vibe}, New vibe: {set_response.vibe}")

    # Get the vibe
    print("Getting current vibe...")
    get_response = stub.GetVibe(example_pb2.GetVibeRequest())
    print(f"Current vibe: {get_response.vibe}")

if __name__ == '__main__':
    run()
