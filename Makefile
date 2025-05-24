PROTO_SRC = protos/example.proto
PY_OUT = .

.PHONY: all proto clean run-server run-client test lint format check-format mypy coverage lint-generated check-all help

# Default target
all: proto

# Show available targets
help:
	@echo "Available targets:"
	@echo "  proto          - Generate protobuf files and MCP code"
	@echo "  clean          - Remove generated files"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run linting on source code"
	@echo "  lint-generated - Run linting on generated MCP code"
	@echo "  format         - Format source code with black and isort"
	@echo "  check-format   - Check if source code is properly formatted"
	@echo "  mypy           - Run type checking with mypy"
	@echo "  coverage       - Run test coverage analysis"
	@echo "  check          - Run all quality checks (tests + linting + formatting)"
	@echo "  check-all      - Run all quality checks including generated code"
	@echo "  run-server     - Start the gRPC server"
	@echo "  run-client     - Run the gRPC client"

proto:
	uv run python -m grpc_tools.protoc -I=. --python_out=$(PY_OUT) --grpc_python_out=$(PY_OUT) --pyi_out=$(PY_OUT) $(PROTO_SRC)
	uv run python -m grpc_tools.protoc -I=. --py-mcp_out=$(PY_OUT) $(PROTO_SRC)

clean:
	find . -path "./.venv" -prune -o -type f \( -name "*_pb2.py" -o -name "*_pb2_grpc.py" -o -name "*_pb2.pyi" -o -name "*_pb2_mcp.py" \) -print | xargs rm -f

run-server:
	uv run python grpc_server.py

run-client:
	uv run python grpc_client.py

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

# Lint generated code from plugin
lint-generated: proto
	@echo "Linting generated MCP code..."
	uv run flake8 protos/*_pb2_mcp.py --exclude=protos/*_pb2.py,protos/*_pb2_grpc.py,protos/*_pb2.pyi || true
	@echo "Generated code linting complete (warnings only)"

# Run all quality checks
check: test lint check-format
	@echo "All quality checks passed!"

# Run all quality checks including generated code
check-all: check lint-generated
	@echo "All quality checks (including generated code) passed!"
