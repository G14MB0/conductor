# Conductor

Conductor is an asynchronous flow orchestrator that executes nodes defined in
configuration files. Each node can run inline Python functions, offload work to
separate processes, or invoke Docker containers. Nodes exchange information by
passing a standard payload structure and can branch to multiple successors based
on execution results.

## Features

- **Single node abstraction** - describe every step with the same schema
  regardless of executor type.
- **Async flow engine** - run nodes concurrently with per-node timeouts.
- **Pluggable executors** - execute Python callables inline, in a process pool,
  or through Docker containers.
- **Shared global state** - inline and process nodes share state without
  explicitly receiving it as a function argument. Docker nodes are isolated by
  design.
- **Remote logging** - optionally ship logs to external services while keeping
  local structured logging.
- **Execution traces & diagrams** - capture run history and export Mermaid
  diagrams that highlight the path taken.
- **CLI & container image** - manage flows from the shell or run everything
  inside Docker.

## How control flow works

Each node receives a `NodeInput` instance and returns a `NodeOutput`. The
`status` contained in the output decides which successors to schedule:

1. The runtime looks up `node.transitions[status]` in the flow definition.
2. Each successor in that list is enqueued and can run concurrently.
3. If no explicit transition matches, `default` is used when present.

Return a plain value, a dictionary, or a full `NodeOutput` - the runtime will
normalise it so the `status` and `data` fields are always available. The sample
`branching` function in `examples/flow_functions.py` demonstrates how returning
`"even"` or `"odd"` selects different branches.

## Docker node I/O contract

Docker nodes run `docker run --rm <image>` and exchange data through stdin/stdout.

- The runtime serialises the `NodeInput` as JSON and writes it to stdin.
- The container should emit a JSON document compatible with `NodeOutput` on stdout.
- Non-zero exit codes mark the node as `error` and capture both stdout and stderr.

The examples include a minimal handler in `examples/docker-node/handler.py` that:

1. Reads the inbound payload from stdin.
2. Mutates the `data` section (e.g. doubling totals, flagging it was processed).
3. Emits a JSON response with an updated `status`, `data`, and `metadata`.

Build the sample image locally:

```bash
docker build -t conductor-example-node ./examples/docker-node
```

The sample flow references that image through the `container` node, so the build
needs to happen before running the flow if you want the Docker step to execute.

## Execution traces and diagrams

The executor records every node invocation, including timings, inputs, outputs,
and the successors that were scheduled. You can export and visualise that
information directly from the CLI.

```bash
# Run a flow, persist the trace, and inspect the shared state
python -m conductor.cli run \
  --flow examples/flow.json \
  --global-config examples/global.json \
  --payload-file examples/payload.json \
  --trace-file examples/last-trace.json \
  --print-state

# Produce a Mermaid diagram and embed per-node statistics
python -m conductor.cli diagram \
  --flow examples/flow.json \
  --trace-file examples/last-trace.json \
  --include-metadata
```

The generated Mermaid output can be pasted into documentation or rendered
through tools such as https://mermaid.live/. Executed nodes and edges are
highlighted, and node labels can include run counts, last status, duration, and
compact representations of the last input/output payloads.

Use `--print-trace` to stream the trace JSON to stdout, or `--print-summary` on
`diagram` to obtain an aggregated JSON report of the execution statistics.

TBN: a bug in Mermaid is known to cut horizontally too long labels. if using --include-metadata
the user can experinece cutted/truncated informations even if the node box is wider then the text

## Configuration overview

Conductor relies on two configuration files:

- **Global configuration** (`global.json`, `global.yaml`, ...): runtime defaults
  such as environment variables, shared state initial values, remote logging and
  container registries.
- **Flow configuration** (`flow.json`, ...): nodes, transitions and starting
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
[`NodeOutput`](conductor/node.py). If a plain value or dictionary is returned itv
is automatically wrapped into a `NodeOutput`. Returning multiple successors runs
them concurrently.

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
  --print-state \
  --print-trace
```

To skip result output, add `--no-print-results`. To store the trace for later
visualisation, use `--trace-file path/to/output.json`.

## Example functions and nodes

The [`examples/flow_functions.py`](examples/flow_functions.py) module contains
reference implementations used by the sample configuration. They demonstrate
inline async functions, process-based work, and interaction with the shared
state. The `examples/docker-node` directory contains the Docker counterpart that
integrates through stdin/stdout.

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
