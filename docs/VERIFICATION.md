# Verification and reproducible experiments

## Run the tests

From the extracted repository root:

```sh
python -m unittest discover -s tests -v
```

The suite checks fixed expected answers, bad inputs, immutable snapshots,
early-stop finality, zero-cost cycles, parallel edges, huge integer arithmetic,
certificate tampering, and command-line behavior. Seeded small graphs are
compared against a separate Floyd–Warshall implementation; its matrix update
schedule is independent of the heap solver. Metamorphic checks include input
ordering, scaling, relabeling, and graph reversal where applicable.

For diagnosis, run one file with the discover pattern:

```sh
python -m unittest discover -s tests -p test_properties.py -v
python -m unittest discover -s tests -p test_io_cli.py -v
```

The verifier has two levels. `verify_route` checks that an edge sequence exists,
is continuous, and has its claimed cost. `verify_distances` independently
establishes full-result optimality using edge inequalities, rooted parent
witnesses, and reachability closure. The CLI uses route verification before
emitting a reachable response.

These checks establish correctness within the supplied graph. They cannot
prove that the input network includes every real road or that a cost model
matches the user's intended objective.

## Run a benchmark

```sh
python -m benchmarks.run --vertices 1000 --edges 6000 --seed 42 --repeats 20 --output results/run-001
```

The command refuses an existing destination. It generates a directed chain
plus random arcs with integer weights from 0 to 20; parallel arcs and self-loops
are allowed. Every vertex is reachable from source 0 through the chain. This
is a synthetic workload, not a road-network or production benchmark.

One warmup precedes timed full-source queries. Each timed result is checked
outside the timer. Construction is measured separately. A separate tracemalloc
pass measures peak Python allocations for the query, excluding graph creation
and process resident memory.

| Output | Meaning |
| --- | --- |
| `graph.json` | Exact generated input accepted by the CLI. |
| `observations.ndjson` | Every repetition's elapsed nanoseconds and work counters. |
| `summary.json` | Median, nearest-rank p95, memory measure, parameters, environment, and digest. |
| `manifest.json` | Completion marker and SHA-256 checksums of the three data files. |

A run directory without a valid manifest is incomplete. Timings are local
observations, not a performance guarantee. A p95 from very few repetitions is
coarse; use more repetitions when investigating tails. Report generator,
parameters, query mode, environment, and all observations when comparing
changes. Never combine observer-enabled and observer-disabled measurements
without labeling that difference.

## Automation and package checks

The included GitHub Actions workflow runs source tests and examples across
Python 3.12, 3.13, and 3.14 on Linux, and Python 3.12 on Windows and macOS. It
also checks package installation. The workflow is ready for a future repository;
its presence is not a claim that remote runs have already passed.

The action configurations follow the official [checkout](https://github.com/actions/checkout)
and [setup-python](https://github.com/actions/setup-python) documentation.
The local validation record is in [VALIDATION.md](../VALIDATION.md).
