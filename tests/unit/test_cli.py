"""Unit tests for the CLI module."""

import sys
from io import BytesIO
from unittest.mock import patch

import pytest
from google.protobuf.compiler import plugin_pb2 as plugin

from src.protoc_gen_py_mcp.cli.cli import main


class TestCLIMain:
    """Test cases for the CLI main function."""

    def test_main_import(self):
        """Test that main function can be imported and exists."""
        assert callable(main)

    def test_main_with_mock_stdin_stdout(self):
        """Test main function with mocked stdin and stdout."""
        # Create a simple, valid request
        request = plugin.CodeGeneratorRequest()
        request.parameter = ""

        # Add empty proto file (will result in no generation)
        proto_file = request.proto_file.add()
        proto_file.name = "empty.proto"
        request.file_to_generate.append("empty.proto")

        request_bytes = request.SerializeToString()

        # Mock stdin and stdout
        with patch("sys.stdin") as mock_stdin, patch("sys.stdout") as mock_stdout:

            # Configure mock stdin
            mock_stdin.buffer.read.return_value = request_bytes

            # Configure mock stdout with a proper mock buffer
            mock_buffer = BytesIO()
            mock_stdout.buffer = mock_buffer

            # Run main
            main()

            # Verify stdin was read
            mock_stdin.buffer.read.assert_called_once()

            # Verify stdout was written to (check the buffer has data)
            assert mock_buffer.tell() > 0  # Buffer position > 0 means data was written

    def test_main_error_handling_with_mock(self):
        """Test main function error handling with mocked IO."""
        # Mock stdin to raise an exception
        with (
            patch("sys.stdin") as mock_stdin,
            patch("sys.stdout") as mock_stdout,
            patch("sys.stderr") as mock_stderr,
        ):

            mock_stdin.buffer.read.side_effect = OSError("Test error")
            mock_stdout.buffer = BytesIO()
            mock_stderr.write = lambda x: None  # Ignore error output
            mock_stderr.flush = lambda: None

            # Main should handle the error and exit
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with code 1
            assert exc_info.value.code == 1

            # Should have attempted to read stdin
            assert mock_stdin.buffer.read.call_count > 0
