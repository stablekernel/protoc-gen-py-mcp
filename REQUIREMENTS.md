Thanks for confirming. I’ll create a revised, detailed development plan for `protoc-gen-py-mcp` that:

* Generates output using raw Python string concatenation (no Jinja/templates)
* Uses the class-based plugin architecture from the manuelzander/python-protoc-plugin example
* Produces standalone Python source files exposing gRPC services as MCP tools
* Maintains full feature parity with the Go plugin including handling enums, optional/repeated fields, and error conversion

I’ll get started and follow up shortly with a step-by-step implementation guide tailored to this architecture.


# Implementation Plan for `protoc-gen-py-mcp` (Python MCP Protoc Plugin)

This plan details how to build a Python-based protoc plugin named **`protoc-gen-py-mcp`** that generates MCP server "glue" code via raw string concatenation. The plugin will convert gRPC service definitions into MCP tools using the Model Context Protocol (MCP) Python SDK. We outline prerequisites, the plugin’s architecture, descriptor parsing, code generation approach, output code structure, packaging, and extensibility considerations.

## Prerequisites

* **Protobuf Compiler (`protoc`)** – Ensure you have a recent version of protoc (v3.15+ recommended for proto3 optional support). Confirm installation with `protoc --version` (expect output like `libprotoc 3.xx`). The plugin will be invoked by protoc, so protoc must be on the PATH.
* **Python 3 Environment** – Develop and run the plugin with Python 3.8+ (for type hints and dataclasses). Install the **Protocol Buffers Python library** matching the protoc version (e.g., `pip install protobuf==3.xx` to get `google.protobuf` runtime). This provides access to `google.protobuf.compiler.plugin_pb2` for the CodeGeneratorRequest/Response message classes.
* **MCP Python SDK** – The generated code will depend on the Model Context Protocol’s Python SDK (e.g., the `mcp` package). Install it via `pip install "mcp[cli]"` (or include in your project’s requirements). This provides `FastMCP` and the `@mcp.tool()` decorator to define tools.
* **Development Tools** – Optionally, set up a virtual environment and install code linters/formatters (like flake8, black) to verify that generated code is PEP8-compliant. Having `protoc` and the plugin script on PATH is essential for testing the plugin (you can also specify the plugin with `--plugin=protoc-gen-py-mcp=path/to/plugin.py` during protoc invocation for development).

## Plugin Architecture

We will follow a class-based plugin architecture similar to Manuel Zander’s Python protoc plugin example. The plugin will be an executable Python script (or module) that reads a CodeGeneratorRequest from stdin and writes a CodeGeneratorResponse to stdout. Key architectural components:

* **Entry Point (`main`)**: The script’s main function reads the serialized `CodeGeneratorRequest` from `sys.stdin.buffer`, parses it into a `plugin_pb2.CodeGeneratorRequest` object, and creates a `plugin_pb2.CodeGeneratorResponse`. It will instantiate the Plugin class to handle the request.
* **Plugin Class**: A `Plugin` class (e.g., `McpPlugin`) will encapsulate the generation logic. This class provides a clean structure and can hold configuration (e.g., any plugin parameters passed via `CodeGeneratorRequest.parameter`). It will have methods such as:

  * `Plugin.handle_file(file_proto)` – generates code for a single `FileDescriptorProto` (representing one .proto file). It returns one or more `CodeGeneratorResponse.File` objects containing filenames and content.
  * `Plugin.generate(request, response)` – orchestrates processing of the request. It will iterate through each `FileDescriptorProto` in `request.proto_file` that was explicitly requested (listed in `request.file_to_generate`). For each, it calls `handle_file` and appends the resulting file(s) to the response.
* **Reading/Writing Protocol Buffers**: Use the `google.protobuf.compiler.plugin_pb2` module for message classes:

  * Read input: `request = plugin.CodeGeneratorRequest.FromString(sys.stdin.buffer.read())`.
  * After generation, write output: `sys.stdout.buffer.write(response.SerializeToString())`.
* **Logging/Errors**: The plugin can use Python’s logging to report progress (e.g., log which files are being processed). If errors occur (e.g., missing types), the plugin should set `response.error` with a message. This ensures protoc reports the error.
* **Testing the Flow**: During development, you can manually test the plugin by running `protoc` with `--py-mcp_out` pointing to a temp directory and `--plugin=protoc-gen-py-mcp=./plugin.py` to ensure the plugin is invoked correctly. The plugin’s name must be `protoc-gen-py-mcp` (matching the `--py-mcp_out` parameter).

## Descriptor Parsing Logic

Parsing the `.proto` definitions from the CodeGeneratorRequest is critical. We will leverage the `FileDescriptorProto` structures to extract services, methods, and message metadata:

* **File Iteration**: The request contains all dependencies, but we only generate code for files explicitly requested (`request.file_to_generate`). For each target file:

  * Retrieve its `FileDescriptorProto` (which includes package name, syntax, message/type definitions, service definitions, etc.).
  * Record the file’s package (if any) for use in imports and naming.
  * Prepare an index of message and enum types for easy lookup by fully-qualified name. We can map `TypeName -> DescriptorProto` for messages and `TypeName -> EnumDescriptorProto` for enums by traversing `file_proto.message_type` and `file_proto.enum_type` (and recursively for nested types). Also include imported types by indexing all `request.proto_file` entries (the CodeGeneratorRequest provides descriptors for imports as well).
* **Service Extraction**: For each `ServiceDescriptorProto` in `file_proto.service`:

  * Get service name (e.g., "MyService") and list of `MethodDescriptorProto` entries.
  * Determine an output filename and module name for this service’s generated code. **Output naming strategy**: we will use the proto file name as base. For example, `myapi.proto` generates `myapi_mcp.py`. (If the proto has multiple services, we will include all in one file for simplicity, with separate factory functions per service. Alternatively, for clarity, one could generate one output per service such as `myapi_MyService_mcp.py`; here we choose one file per .proto for easier packaging of modules.)
* **Method Extraction**: For each RPC `MethodDescriptorProto` in a service:

  * Collect the method name (e.g., "DoSomething"). We will use this to name the tool function.
  * Get the input and output message types (e.g., `.package.InputMessage`). The descriptor gives fully-qualified type names. Use the descriptor index to find the actual `DescriptorProto` for the input and output message definitions (which may be in the same file or an imported file).
  * **Input Message Fields**: Retrieve each field in the input message (`FieldDescriptorProto`). For each field:

    * Note the field name (we will use it as a parameter name in snake\_case, which typically matches proto naming since proto field\_names are lowercase\_with\_underscores by convention).
    * Determine the field’s type and label:

      * *Primitives*: Map proto types to Python types for function signatures. For example: `TYPE_BOOL` -> `bool`, `TYPE_STRING` -> `str`, `TYPE_INT32/INT64` -> `int`, `TYPE_FLOAT/DOUBLE` -> `float`, `TYPE_BYTES` -> `bytes`, etc. This will ensure generated functions have informative type hints.
      * *Enums*: If the field type is an enum, we will treat it as `int` in the tool function signature (since the tool will receive a numeric or we will convert name to number internally). We note the enum’s name to possibly document it. The generator will ensure to convert enum names to numeric values in outputs and expect numeric inputs for simplicity (we can later extend to accept enum names). **Enum mapping**: use `json_format` with `use_integers_for_enums=True` to output numeric codes for enums. If needed, input handling can map enum name strings to their numeric value via the pb2 enum class (e.g., `MyEnum.Value("NAME")`).
      * *Messages*: If a field is a message (nested object), for now we will use a generic approach. We can type hint it as a dict (or a specific pb2 message class). Since MCP tools exchange JSON, we may accept a Python dict for complex message fields. The generated code could use `json_format.ParseDict` to convert a dict to the appropriate message type inside the function.
      * *Repeated Fields*: If `field.label == LABEL_REPEATED`, the parameter will be a `List` of the element type. We’ll import `List` from `typing` and use e.g. `List[int]` or `List[MyMessage]` in the signature. The code will accept Python lists for these fields. When constructing protobuf messages, the list can be passed directly (protobuf will handle repeated field assignment from Python lists).
      * *Optional Fields*: Proto3 optional fields are indicated by `field.proto3_optional = True` in the descriptor and are implemented via a synthetic oneof internally. We will detect `proto3_optional` and **not** treat it as a real oneof in generation (to avoid confusion – synthetic oneofs exist only to signal presence and generate no separate API). For optional fields:

        * We will mark the parameter as optional in Python: use `Optional[type]` from `typing` in the hint, and give it a default of `None`. This way, if the client omits the field, the function can be called without that argument (or with `None`).
        * In the generated code, when constructing the protobuf request message, we will only set the field if the corresponding Python argument is not `None`. If it is `None`, the field remains unset (preserving absence).
  * **Output Message Handling**: We will use `google.protobuf.json_format` utilities to serialize the RPC response message to a form suitable for MCP:

    * After computing or obtaining the response (which for now might be a placeholder), convert the `Message` to a Python dict using `json_format.MessageToDict(response, use_integers_for_enums=True)`. This ensures any enum fields are represented as integers in the output JSON structure.
    * If the output message is very simple (e.g., a single primitive or an `Empty` type), we handle accordingly:

      * For `google.protobuf.Empty` outputs, the tool function can return `None` or an empty dict since there’s no data.
      * If the output has one primitive field, we might directly return that field’s value (for simplicity). But to keep consistency, we will typically return a dict (the full JSON object) or a primitive. The MCP framework will serialize the result to JSON for the client. (For example, returning a dict or list will be JSON-encoded by MCP; returning a primitive will be encoded as well).
    * By using `MessageToDict`, we get a clean Python-native object (dict) that MCP will likely handle. Alternatively, one could use `MessageToJson` to get a JSON string, but returning a Python dict is preferable for structured data (the MCP server will serialize it to JSON).
* **Service Name and Tool Registration**: Determine how to name the MCP tools. By default, the MCP SDK will use the function name as the tool name. We will use the RPC method name (possibly in lowercase or snake\_case if needed for Python conventions). For clarity and to avoid name collisions, we might prefix the tool name with the service name or not:

  * If multiple services are in one server instance, prefixing could avoid collisions. However, in our approach each service can be exposed via its own server factory, so tool names can remain as defined in proto (lowercased for Python function naming if proto used UpperCamel for method). E.g., proto method `GetUser` -> Python function `get_user` as tool name.
  * We will preserve method naming but adapt to Python style (camelCase -> snake\_case) for the function definition to be PEP8-compliant. (We’ll derive snake\_case from the proto name for the function, but the MCP `title` annotation could use the original name as a human-friendly title if desired).

## Code Generation via String Concatenation

We will generate the Python source code as text, using **raw string concatenation** (no templating engine). The design will ensure correct indentation and formatting:

* **String Assembly Strategy**: We will build output code by concatenating strings or using multiline f-strings. A small utility within the plugin can help manage indentation levels (e.g., maintain an `indent` string that is appended to each line for proper formatting).

  * Start with an empty list of lines for each output file, or use a `io.StringIO` buffer.
  * Define helper functions like `w(line="", level=0)` that appends `("    "*level) + line + "\n"` to the buffer, making it easy to manage indent levels instead of manual spacing.
* **No External Templates**: All code will be inlined in Python. For example, to add an import line:
  `code_lines.append(f"from {pb2_module} import {msg_class} as {alias}")`. We will carefully construct multi-line blocks (like function definitions) by writing each line with the appropriate indent.
* **PEP8 Formatting**: The generator will produce code that is already formatted according to PEP8:

  * Use 4 spaces per indent level.
  * Lines not exceeding 79-100 characters where possible (split string literals or lines if needed).
  * Two blank lines before top-level function definitions or between class definitions (if any).
  * Include necessary imports at top, and group them logically (stdlib vs third-party vs local imports).
  * Use snake\_case for function and variable names (including converting proto names as needed). Constants (if any) in all-caps, etc.
  * Trailing whitespace and other common lint issues will be avoided in the string literals.
  * We may run the generated code through `flake8` or `black` during development to verify compliance, adjusting the generator as needed (this is a one-time effort to ensure the template logic produces clean code).
* **Example Snippet Construction**: For each service, the code generator might do something like:

  ```python
  w(f"class {service_name}McpPlugin:")
  w('    """MCP glue code for the service ' + service_name + '"""', 1)
  w(f"def create_{service_name}_server():", 0)
  w(f'    """Create an MCP server for {service_name} service tools."""', 1)
  w("    mcp = FastMCP(\"{service_name}\")", 1)
  # For each method:
  w(f"    @mcp.tool()", 1)
  func_def = f"    def {method_name_py}("
  # add params...
  func_def += ") -> {ret_type}:"
  w(func_def, 1)
  w('        """Tool handling for RPC ' + method.name + '"""', 2)
  w("        # Construct request message", 2)
  w(f"        request = {pb2_module}.{input_type_class}()", 2)
  w("        # Populate request fields", 2)
  ...
  w("        # TODO: implement actual logic", 2)
  w(f"        response = {pb2_module}.{output_type_class}()", 2)
  w("        # ... user logic to fill response ...", 2)
  w("        result_dict = json_format.MessageToDict(response, use_integers_for_enums=True)", 2)
  w("        return result_dict", 2)
  ```

  The above is a conceptual example of how the plugin will construct code via string writing functions. The actual generator will handle insertion of actual types and field assignments as needed.
* **Inline Handlers**: Note that we decorate and define the tool functions inline (within the server creation function). This ensures when `create_<Service>_server()` is called at runtime, it registers the tool handlers with that server’s `FastMCP` instance. The use of the decorator inside the factory function binds the tool to the local `mcp` instance. We must be careful that the decorator is applied at function definition time when `create_server` is called, not at import time. (Defining them inside the factory ensures each call creates a fresh FastMCP with tools bound.)
* **Avoiding Templating Pitfalls**: We will double-check that special characters (like braces in f-strings or percent signs) are properly escaped or handled when concatenating. For example, when generating code that itself contains f-string braces or format strings, ensure we use double braces `{{ }}` in our generation strings to produce a single brace in output, if needed.

## Generated Code Structure

Each output Python file will be a self-contained module exposing the MCP server for the given proto services. The structure of a typical generated file:

1. **Module Docstring/Comment**: (Optional) We may begin with a brief comment indicating that the file is auto-generated by protoc-gen-py-mcp, and advising not to edit manually. This is standard for generated code.
2. **Imports**: The top of the file will import necessary modules:

   * `from fastmcp import FastMCP` – FastMCP server class.
   * `from mcp import tool` or `@mcp.tool` decorator (depending on SDK specifics; in the SDK, `mcp.tool()` is a method of FastMCP via decorator, not a global, so we actually will use the instance’s decorator).
   * `from google.protobuf import json_format` – to use `json_format.MessageToDict` (and possibly `MessageToJson` if needed).
   * Protobuf generated classes for messages and enums:

     * e.g. `import myservice_pb2 as myservice_pb2` and possibly `import myservice_pb2_grpc as myservice_pb2_grpc` (though we might not need pb2\_grpc since we’re not using gRPC stubs here, just message classes).
     * If the proto’s Python package differs or the file is in a subdirectory, we adjust the import. For instance, if `file_proto.package = "foo.bar"` and/or a `FileOptions.python_package` is set, we use that to form the import path (e.g., `from foo import bar__myservice_pb2 as myservice_pb2`). By default, we assume the pb2 module is accessible via the proto file’s basename plus `_pb2`. We ensure our output file uses the same package structure as the pb2 to make relative imports possible. (For example, if `example.proto` is in package `foo`, we might output `foo/example_mcp.py` with an import for `foo/example_pb2.py`).
     * Additionally, we will `from typing import Optional, List, Dict` as needed for type hints (Optional for proto3 optional fields, List for repeated fields, Dict for possibly dict inputs/returns).
     * If any dataclasses or other stdlib are needed, import those (e.g., we might use `dataclasses.dataclass` for representing a simplified response, but likely not needed if we use dicts directly).
3. **MCP Server Factory Functions**: For each service in the proto file, we generate a factory function to create a configured MCP server:

   * Function name: `create_<ServiceName>_server`. For example, `create_UserService_server()`. We use CamelCase service name as in proto, or possibly snake\_case; but to clearly separate words we might keep CamelCase part and add `_server`. (PEP8 says function names should be lowercase, so `create_user_service_server` could be used. However, including the service name in CamelCase is sometimes acceptable for generated code to mirror the proto name. We will likely opt for lowercase with underscores for full compliance: e.g., `create_user_service_server`.)
   * This function will:

     * Instantiate a FastMCP server: `mcp = FastMCP("<ServiceName>")`. The name can be the service name or some identifier for the server. (The string name is typically a human-readable name for the server; using the service name makes sense if one service per server. If the server might include multiple services, a generic name or combine names could be used. We’ll assume one service per server instance for clarity.)
     * Register each RPC method as an MCP tool. We do this by defining a Python inner function for each method and decorating it with `@mcp.tool()`.

       * **Tool Function Definition**: This inner function’s name will mirror the RPC method (converted to snake\_case). Its parameters correspond to the RPC input message fields. Each parameter will have type hints as determined in parsing (including `Optional` and `List` as needed, and primitive types or possibly dict for sub-messages). If the input message is empty (`google.protobuf.Empty`), the function will have no parameters (just `()`). If there’s a single field, we’ll still take it as a parameter rather than a message object.
       * The return type hint will generally be a Python type corresponding to the RPC output. If the output is a primitive (e.g., an int or string), we return that type. If it’s a message, we will hint as `Dict[str, Any]` (or simply no specific type or `dict`) since we return a dict representation. For simplicity, we might use `-> dict` or `-> Any` for complex outputs, but documenting it is good. We want readable code, so using `-> dict` is fine to indicate JSON output.
       * **Function Body**: The generated body will include:

         * (Optional) Construction of the request message object from inputs. If the code is meant to be “glue” that calls an existing implementation (e.g., if the user has separate gRPC server/client), we might instead call that. In this plan, we assume the user will implement the logic within this function (or call out to library functions) – we provide the skeleton. So we will show how to convert input parameters into a protobuf **request** object if needed, and then show a placeholder for actual logic.
         * For now, we can simply mark a **TODO** or placeholder comment like `# TODO: Implement the business logic for <MethodName>` or raise `NotImplementedError`. If we want to encourage usage of existing gRPC code, we could suggest calling a stub:

           * e.g., `# NOTE: You could call an existing gRPC service here using generated stubs if available`.
         * Preparation of **response**: We create an instance of the output message class (`response = pb2.<OutputType>()`).
         * If we had a real implementation, we’d populate `response` accordingly. In the template, we might either leave it empty or populate with dummy data for demonstration. Better to leave fields blank or zeros and let user fill in.
         * Serialize the response: Use `json_format.MessageToDict(response, use_integers_for_enums=True)` to get a `result_dict`.
         * `return result_dict` as the output of the tool function. (If the output was a single primitive, an alternative is to extract that value and return it directly, but using dict uniformly is fine. Alternatively, for better readability, if the output message has fields, we might unpack them: e.g., if output has fields `id` and `name`, one could return `{"id": response.id, "name": response.name}`. However, using json\_format ensures all fields (including nested) are handled systematically, so we prefer that approach.)
         * **Enum Handling**: Because we set `use_integers_for_enums=True`, any enum field in the response will appear as its numeric value in `result_dict`. This aligns with typical MCP usage (ensuring consistent numeric outputs for enums).
         * **Optional Fields in Output**: If some fields of the output are optional and not set, `MessageToDict` will by default omit them from the dict (unless we specify including default). This is acceptable; absent fields simply won’t appear in the JSON, indicating they are not set.
         * **Error Handling**: If an error occurs in the tool logic, the function could raise an exception which MCP will propagate as an error response. We won’t generate any explicit try/except; we assume user will handle if needed. Possibly, as an extensibility note, we could wrap execution and return a structured error in MCP format.
       * We will attach a docstring to each tool function. Ideally, this could include the proto’s documentation comments. If source info is accessible (by enabling protoc’s `--include_source_info` parameter), the plugin could extract the comments for the service or method and use them. In absence of that, we can at least document the parameters and return briefly:

         * For example: `""" Implements the {MethodName} RPC. \n\n Args:\n    field1: <field type> description...\n Returns:\n    dict: JSON serializable dict of {OutputType}."""`. At minimum, stating it's an MCP tool for the RPC and listing fields can guide the user. This contributes to readable, self-documenting output code.
     * After defining all tool functions for the service, the factory function ends with `return mcp`. This returns a configured `FastMCP` server instance with all tools registered.
   * The user can then use this factory to instantiate the server in their application (or potentially we could also generate a `main` block to run the server for quick testing, though not required).
4. **Multiple Services**: If a proto file contains multiple services, the output file will contain multiple `create_<Service>_server` functions and their respective tool definitions. They will each create separate `FastMCP` instances. We will ensure function names and internal variables are distinct per service to avoid collisions. (E.g., use `mcp = FastMCP("ServiceA")` in one function and a fresh `mcp = FastMCP("ServiceB")` in another – since they are in separate functions, using the same variable name is fine due to scope, but we should not mix tools between them.)

   * If the user wants a single MCP server to host all service tools together, they could easily combine after generation (e.g., by creating one FastMCP and registering all tools, or by modifying the code). As an extensibility idea, we could generate an option for that, but by default we keep them separate for clarity.
5. **PEP8 and Readability**: The generated code will be designed to look like hand-written Python as much as possible:

   * Proper spacing around operators, no extraneous parentheses, clear naming.
   * Avoid deeply nested logic in generated code – keep each tool handler relatively flat in structure (since it mainly constructs messages and returns results).
   * Possibly include **comments** in the generated code for clarity. E.g., comments delineating sections (`# Imports`, `# MCP server and tool definitions for ServiceX`, `# Construct request`, `# Serialize response`, etc.). This helps users or contributors understand the glue code.
   * Ensure that line breaks occur at sensible places. If a function signature is very long (many parameters), consider breaking it into multiple lines for readability. Our generator can detect number of params and insert a newline + indent if needed.
   * The output code should be immediately usable in an IDE, and passing typical linters (we can mention that we tested it with flake8/black).
   * Example generated function signature for context:

     ```python
     @mcp.tool()
     def get_user_info(user_id: int, include_history: bool = None) -> dict:
         """Tool handling for RPC GetUserInfo."""
         # Construct request message
         request = myapi_pb2.GetUserInfoRequest()
         if user_id is not None:
             request.user_id = user_id
         if include_history is not None:
             request.include_history = include_history
         # TODO: Implement actual logic to populate the response
         response = myapi_pb2.GetUserInfoResponse()
         # For now, return an empty or default response
         result = json_format.MessageToDict(response, use_integers_for_enums=True)
         return result
     ```

     In this example, `include_history` was an optional field (defaulting to None), and we handle it conditionally. This code is cleanly structured and ready for the user to fill in the logic.

## Packaging and Installation

To make the plugin easy to install and use (including publishing to PyPI), we will prepare packaging configuration:

* **Python Package Structure**: Organize the plugin code in a Python package (e.g., a directory `protoc_gen_py_mcp/` with an `__init__.py`). The main plugin script could be `protoc_gen_py_mcp/main.py` or similar, containing the `main()` function that executes the plugin. This separation allows us to use a console entry point.
* **Setup Script (setup.py or pyproject.toml)**: Define a package name (e.g., `"protoc-gen-py-mcp"`) and appropriate metadata (version, description, authors, dependencies). Notably:

  * **Entry Point**: Use `setuptools` entry\_points to create a console script. For example, in setup.py:

    ```python
    entry_points={
        'console_scripts': [
            'protoc-gen-py-mcp = protoc_gen_py_mcp.main:main'
        ],
    }
    ```

    This will install an executable script `protoc-gen-py-mcp` in the user’s PATH. Protoc will automatically find `protoc-gen-py-mcp` when the user specifies `--py-mcp_out` during code generation (because protoc looks for a program named “protoc-gen-<name>”).
  * **Dependencies**: List `protobuf` and `mcp` (and any others like typing\_extensions if used) in `install_requires` so that users get them when installing the plugin. However, note that the plugin itself uses `google.protobuf.compiler.plugin_pb2` which is part of `protobuf` package, and it expects protoc to be installed separately. We should document that protoc itself is not installed via pip.
  * **PyPI Metadata**: Fill in classifiers (Programming Language :: Python, etc.), license, project URLs (source code repo), and a long\_description (README) explaining usage.
* **Installation**: Once published, users can do `pip install protoc-gen-py-mcp`. This will provide the plugin script. They can then invoke protoc with `--py-mcp_out=<out_dir>` (assuming protoc is configured to find the plugin on PATH). For example:

  ```bash
  protoc -I proto_dir --py-mcp_out=generated_code_dir myservice.proto
  ```

  This will produce the `_mcp.py` files in `generated_code_dir`. If the plugin is not on PATH, users can also use the `--plugin` flag to specify the path to `protoc-gen-py-mcp`.
* **Shebang**: Ensure the entry script has a shebang like `#!/usr/bin/env python3` if needed for direct execution (though console\_scripts handles it).
* **Testing Distribution**: Before publishing, test the installation locally (e.g., using `pip install .` in a fresh virtualenv) to confirm that the `protoc-gen-py-mcp` command is installed and functional (`which protoc-gen-py-mcp` should show it in the environment). Then, using `protoc --py-mcp_out=.` on a sample proto should trigger our plugin.
* **Publishing to PyPI**: Use standard tools to publish:

  * Make sure the package name `protoc-gen-py-mcp` is available on PyPI. (If not, choose a different distribution name but the console script must still be named protoc-gen-py-mcp for protoc to pick it up).
  * Build the distribution (`python -m build` or `setup.py sdist bdist_wheel`) and upload with Twine.
  * Once on PyPI, users can install it as described.
* **Versioning**: Follow semantic versioning. Starting with a 0.1.0 for experimental, and increment as features are added. Communicate clearly in the README which protoc and protobuf versions are supported (especially if proto3 optional requires specific minimum versions of protoc/protobuf).
* **Package Organization**: Keep the plugin code minimal and focused. We might place our `Plugin` class in a module (e.g., `plugin_logic.py`) and the `main` in `__main__.py` or `main.py` that calls into it. This allows `python -m protoc_gen_py_mcp` to run as well.
* **Executable Script on Windows**: The console\_scripts entry will create a `protoc-gen-py-mcp.exe` on Windows or a stub launcher, so cross-platform use is ensured.

## Extensibility and Future Improvements

The initial implementation provides basic functionality, but we should design it to be extensible for future needs:

* **Extend to More Proto Features**: The plan covers services, standard field types, optional, repeated, and enums. Future improvements:

  * **Oneof Fields**: Currently, we handle proto3 optional (synthetic oneofs) by treating them as optional fields. We may also want to handle real oneofs (where only one of several fields may be set). In code generation, we could represent a oneof by either choosing one field at a time or by providing multiple function signatures (not possible directly) or requiring the user to only fill one. For now, we might simply generate all fields and document that only one should be provided at a time. A more complex approach could be to generate separate tool variants for each oneof case, but that's likely overkill. This area could be refined as needed.
  * **Map Fields**: Proto map fields appear as repeated entries of a synthetic message type (with key and value). We can detect maps via `FieldDescriptorProto.type == TYPE_MESSAGE` and the message name ends with "Entry" with options indicating it’s a map. We could then represent it as a `Dict[key_type, value_type]` in the function signature. Initially, we might treat them as generic repeated of a message and improve later. Extending to output proper dicts for maps (which `MessageToDict` does automatically) is also possible.
  * **Streaming RPCs**: If proto services include server or client streaming RPCs, our generator currently is not handling those (MCP tools are request/response oriented, not streaming). We might choose to ignore streaming methods or generate a warning. In the future, if MCP supports some streaming interaction, we could map streaming RPCs to such patterns.
* **Integration with gRPC Implementations**: The glue code could be extended to call actual gRPC service implementations:

  * For example, if a user already has a gRPC server running, the MCP tool function could act as a client: create a gRPC stub and forward the request, then take the response and return it as JSON. This would require additional context (server address, and importing `grpc` and the pb2\_grpc module). We could add plugin parameters to specify a target (e.g., `--py-mcp_out=grpc_host=localhost:50051:` to generate code that connects to that host). This is an advanced use-case; our base plan will not implement it, but the structure (with clearly separated codegen for request, call, and response) can accommodate insertion of such logic.
  * Alternatively, if the user wants to implement the logic in the generated file itself, they can do so by filling in the TODO sections. To prevent overwriting custom logic on re-generation, one could extend the plugin to preserve user code blocks (e.g., special delimiters to only generate stubs if not edited). This is complex and not done initially, but noted for future enhancement.
* **Customization via Parameters**: protoc plugins allow a parameter string (CodeGeneratorRequest.parameter). We can design our plugin to accept options, for example:

  * `package=` or `no_package_dir` to control if we create package directories.
  * `combined_server=` to generate one combined server for all services in a file.
  * `use_async=` to generate `async def` tool functions (if we want to support async tool execution in MCP, as MCP does allow async definitions as seen in documentation).
  * `annotations=` to include MCP tool annotations (like titles, descriptions) extracted from proto comments. E.g., use proto documentation as the tool description annotation. This could enrich the generated tools. For instance, we might automatically add `annotations={"title": "My Method", "description": "<from proto comments>"}` in the `@mcp.tool()` decorator.
  * We should structure the Plugin class to easily read and apply such parameters. For now, we will implement with sensible defaults and leave hooks for these options.
* **Testing & Validation**: As we extend, maintaining tests is crucial. We can create sample .proto files (covering optional fields, enums, repeated, etc.) and have the plugin generate code, then write tests that import the generated code and simulate calling the tools:

  * For example, ensure that calling the tool function with various inputs yields a dict that matches the expected `json_format` output of an equivalent manually constructed message. This ensures our serialization logic works.
  * If possible, spin up the MCP server and call it via an MCP client (the SDK’s testing utilities or the inspector) to ensure end-to-end functionality.
* **Performance Considerations**: For large protos with many services/methods, string concatenation is fine (the data sizes are moderate). But if needed, we could optimize generation by using templates in-memory (like Python format strings) to avoid repetitive concatenation. However, given that plugins run quickly within protoc, the current approach should be sufficient.
* **Keeping Up-to-date**: Monitor updates to the MCP Python SDK and protobuf library:

  * If the MCP API changes (for example, the decorator usage or server initialization), update the generator accordingly.
  * If new protobuf features emerge (e.g., new scalar types or well-known types handling), include support.
  * Ensure our generated code remains compatible with future Python versions (especially regarding type hints syntax, e.g., using `list[int]` instead of `List[int]` in Python 3.9+, etc.).
* **Community Feedback**: Encourage users to file issues or contributions. Perhaps set up the repository on GitHub for collaboration. Future improvements might include using a small templating within code (like f-string templates) if needed, but we will adhere to no external templating engine requirement.

By following this plan, the `protoc-gen-py-mcp` plugin will systematically translate .proto service definitions into clean, Pythonic MCP server code. The output will allow developers to quickly expose gRPC-defined functionality as MCP tools, speeding up integration with LLM applications. The approach ensures clarity (through direct string generation and comments) and maintainability, while the packaging steps will make adoption and distribution straightforward.

**Sources:**

* Google’s definition of protoc plugins and basic plugin structure.
* Handling of proto3 optional fields and synthetic oneofs.
* Usage of `json_format` for enum and message JSON conversion.
* Example entry point for packaging protoc plugins as console scripts.
