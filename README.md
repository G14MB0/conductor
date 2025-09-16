# Conductor

Conductor is an asynchronous flow orchestrator that executes nodes defined in
configuration files. Each node can run inline Python functions, offload work to
separate processes, or invoke Docker containers. Nodes exchange information by
passing a standard payload structure and can branch to multiple successors based
on execution results.

## Features

- **Single node abstraction** – every step is described through the same
  configuration schema regardless of how it is executed.
- **Async flow engine** – runs nodes concurrently according to the configured
  transitions and honours per-node timeouts.
- **Pluggable executors** – execute Python callables inline, in a process pool,
  or through Docker containers.
- **Shared global state** – inline and process nodes share a common state object
  without needing to receive it as function arguments. Docker nodes are
  isolated by design.
- **Remote logging** – optionally ship logs to external services while keeping
  local structured logging.
- **CLI tooling** – manage flows from the shell with `python -m conductor.cli`.
- **Docker ready** – container image for easy deployment.

## Configuration overview

Conductor relies on two configuration files:

- **Global configuration** (`global.json`, `global.yaml`, …) – runtime defaults
  such as environment variables, shared state initial values, remote logging and
  container registries.
- **Flow configuration** (`flow.json`, …) – nodes, transitions and starting
  points for a specific workflow.

### Flow configuration schema

```jsonc
{
  "name": "example",
  "start": ["start"],
  "nodes": [
    {
      "id": "start",
      "executor": "inline",          // inline | process | docker
      "callable": "package.module:function",
      "timeout": 5.0,
      "env": {"KEY": "VALUE"},       // merged with global env for the node
      "transitions": {
        "success": ["next-node"],     // branching on NodeOutput.status
        "error": ["fallback"]
      }
    }
  ]
}
```

Each node receives a [`NodeInput`](conductor/node.py) instance and returns a
[`NodeOutput`](conductor/node.py). If a plain value or dictionary is returned it
is automatically wrapped into a `NodeOutput`. The `status` field decides which
transition to follow (`default` is used when no matching status exists).
Returning multiple successors executes them concurrently.

### Global configuration schema

```jsonc
{
  "env": {"EXAMPLE_FLAG": "enabled"},
  "shared_state": {"start_invocations": 0},
  "remote_logging": {
    "target": "http://logging.example.com/ingest",
    "method": "POST",
    "enabled": false
  },
  "container_registries": ["registry.example.com/library"],
  "process_pool_size": 2,
  "max_concurrency": 4
}
```

`shared_state` values are preloaded into the global state object that can be
accessed from node implementations via:

```python
from conductor.global_state import get_global_state

state = get_global_state()
current_value = state.get_sync("key", 0)
state.set_sync("key", current_value + 1)
```

## Command line usage

Install dependencies (standard library only) and run the CLI:

```bash
python -m conductor.cli run \
  --flow examples/flow.json \
  --global-config examples/global.json \
  --payload '{"number": 6}' \
  --print-state
```

The command loads the configuration, executes the flow and prints terminal node
outputs. Use `--no-print-results` to suppress result output and
`--print-state` to inspect the shared state after execution.

## Example functions

The [`examples/flow_functions.py`](examples/flow_functions.py) module contains
reference implementations used by the sample configuration. They demonstrate
inline async functions, process-based work, and interaction with the shared
state.

## Docker image

Build a container image that bundles the CLI:

```bash
docker build -t conductor:latest .
```

Run the flow inside the container:

```bash
docker run --rm -v "$PWD":/app conductor:latest \
  python -m conductor.cli run --flow examples/flow.json --payload '{"number": 3}'
```

Override configuration files by mounting them into the container or by setting
environment variables through the CLI or node definitions.

## Development

- `python -m conductor.cli run --help` shows all CLI options.
- The package is designed to be dependency-free; optional YAML/TOML support is
  enabled when `pyyaml` or the standard `tomllib` module are available.
- Nodes executed in Docker rely on `docker run` being available on the host.

## License

MIT
