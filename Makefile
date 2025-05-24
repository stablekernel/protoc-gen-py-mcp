PROTO_SRC = protos/example.proto
PY_OUT = .

.PHONY: all proto clean run-server run-client test lint format check-format mypy coverage

all: proto

proto:
	python -m grpc_tools.protoc -I=. --python_out=$(PY_OUT) --grpc_python_out=$(PY_OUT) --pyi_out=$(PY_OUT) $(PROTO_SRC)
	python -m grpc_tools.protoc -I=. --py-mcp_out=$(PY_OUT) $(PROTO_SRC)

clean:
	find . -path "./.venv" -prune -o -type f \( -name "*_pb2.py" -o -name "*_pb2_grpc.py" -o -name "*_pb2.pyi" -o -name "*_pb2_mcp.py" \) -print | xargs rm -f

run-server:
	python grpc_server.py

run-client:
	python grpc_client.py

test:
	uv run pytest tests/ -v

# Linting and formatting
lint:
	uv run flake8 src tests
	uv run mypy src

format:
	uv run black src tests
	uv run isort src tests

check-format:
	uv run black --check src tests
	uv run isort --check-only src tests

mypy:
	uv run mypy src

coverage:
	uv run coverage run -m pytest tests/
	uv run coverage report
	uv run coverage html

# Run all quality checks
check: test lint check-format
	@echo "All quality checks passed!"
