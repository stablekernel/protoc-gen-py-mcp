PROTO_SRC = protos/example.proto
PY_OUT = .

.PHONY: all proto clean run-server run-client

all: proto

proto:
	python -m grpc_tools.protoc -I=. --python_out=$(PY_OUT) --grpc_python_out=$(PY_OUT) --pyi_out=$(PY_OUT) $(PROTO_SRC)
	# protoc --py-mcp_out=$(PY_OUT) $(PROTO_SRC)

clean:
	find . -type f -name "*_pb2.py" -o -name "*_pb2_grpc.py" -o -name "*_pb2.pyi" -o -name "*_pb2_mpc.py" | xargs rm -f

run-server:
	python grpc_server.py

run-client:
	python grpc_client.py
