# Contributing

Start by running `python -m unittest discover -s tests -v`. Keep the core and
test suite runnable with Python 3.12 and the standard library. Changes to
accepted inputs, result finality, tie policy, or serialized fields are API
changes and need documentation and regression coverage.

For a bug, record a small graph, source, target, expected cost, observed output,
Python version, and the graph digest. Replace private network labels and data
before sharing the example. A minimal failing fixture is usually more useful
than a large production dataset.

For code changes:

1. State the incorrect behavior or new use case.
2. Add a test that distinguishes the proposed behavior from the old behavior.
3. Keep route verification independent of the shortest-path solver.
4. Run tests and relevant examples. Check packaging if you change the public API.
5. Update the guides and changelog when behavior changes.

Avoid timing assertions in unit tests. Benchmark optimizations on identical
graphs and query modes, verify answers, and retain all raw observations. Do
not weaken validation or accept provisional labels to improve timings.

The GitHub Actions workflow runs the tests and examples once this folder is
published as a repository. Its configuration is included; a remote run is not
part of the local release validation.
