protoc-gen-lang-mcp
-----------
This is a [Topeka](#topeka) plugin for the [protoc compiler](https://grpc.io/docs/protoc-installation/) that generates a [model-context-protocol(MCP)](https://modelcontextprotocol.io/introduction) server based on a [protocol buffer](https://protobuf.dev/) definition. Conceptually, this allows an AI model to use existing [gRPC](https://grpc.io/) codebases with natural language, allowing for rapid prototyping and usage of LLM capabilities for protobuf based codebases.

#### Prerequisites
- [protoc](https://grpc.io/docs/protoc-installation/) 3.20 or later
[TODO: add all prerequisites to successfully build and run the plugin]

#### Running the plugin
[TODO: add instructions to run the plugin]

#### Debugging the plugin
[TODO: add instructions to debug the plugin]

#### Testing the example
Install the example `mcp-vibe` server
[TODO: add instructions to run the project specific example server]
Add the `mcp-vibe` server to your mcp servers:
```json
{
  "mcpServers": {
    "vibe": {
      "command": "mcp-vibe"
    }
  }
}
```
and run a client with above mcp server attached (eg. claude desktop)

#### Topeka
[Topeka](https://topeka.ai) is an open source project that provides code-generators for [Model-Context-Protocol (MCP)](https://modelcontextprotocol.io/introduction).
It is designed to facilitate the usage of MCP seamlessly against existing gRPC based applications. This is done via
leveraging code generation using the [protoc compiler](https://grpc.io/docs/protoc-installation/) and installing the relevant Topeka plugin.

The plugins follow [Semantic Versioning](https://semver.org/) and any plugin prior to 1.0.0 releases ARE still subject to breaking changes. Please note, this is
applied to the generated servers, not the plugins themselves, which do not provide public APIs. This project reserves the right to change how code generation is achieved,
while maintaining stable MCP server APIs.

#### Maintainers
[Stable Kernel](https://stablekernel.com) is the primary maintainer of this project and sponsor of the plugins, though we welcome outside contributions.

[Stable Kernel](https://stablekernel.com) is a digital transformation company building solutions that power LLM enablement for growing businesses. We have a track record of helping our partners solve their biggest challenges on their digital journey, whether they need insights or implementation. Every day, millions of people rely on software that we developed, and our custom software development and technology services have been trusted by some of the most innovative Fortune 500 companies in the world. 
