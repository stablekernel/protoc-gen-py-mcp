PROTO_SRC = protos/example.proto
PY_OUT = .

.PHONY: all proto clean run-server run-client

all: proto

proto:
	python -m grpc_tools.protoc -I=. --python_out=$(PY_OUT) --grpc_python_out=$(PY_OUT) $(PROTO_SRC)
	protoc --pyi_out=$(PY_OUT) $(PROTO_SRC)

clean:
	rm -f *_pb2.py *_pb2_grpc.py

run-server:
	python grpc_server.py

run-client:
	python grpc_client.py
