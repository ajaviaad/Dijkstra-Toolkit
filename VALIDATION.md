# Release validation

Version 0.1.0 was validated locally on 8 October 2026 with Python 3.12.14 on
macOS ARM64. The checks below describe this release, not every possible
platform or future revision.

- 59 unit, property, certificate, input-format, and CLI tests passed.
- The differential suite compared 100 seeded small graphs against independent
  Floyd–Warshall distances, including all sources and targets. Additional
  multi-source, reverse-graph, and metamorphic checks passed.
- All six application examples produced their expected answers.
- README and API Python examples executed successfully.
- The A–G fixtures matched their stored route and all-pairs matrix. Inline JSON
  and checksummed NDJSON representations produced the same graph identity.
- A benchmark smoke run used 100 vertices, 600 arcs, seed 42, and five measured
  repetitions. Its generated graph, observations, and manifest checksums were
  checked. These observations are validation, not performance claims.
- Benchmark edge cases with one vertex and no edges, self-loops, and a
  two-vertex chain passed, as did refusal to overwrite existing reports.
- A wheel was built offline, installed into a clean virtual environment, and
  its console command returned the expected A–G route from outside the source
  folder.
- A freshly extracted archive passed all 59 tests and all six CLI commands.
  Documentation links were checked, and generated build files and caches were
  excluded from the release archive.

The repository includes a cross-platform GitHub Actions workflow. Remote CI
has not been run because this archive has not been published to a remote
repository. Python 3.13/3.14 and Windows/Linux support are configured for CI
but were not executed in this local environment.

To reproduce the main checks, run `python -m unittest discover -s tests -v`,
the six commands in the README examples section, and the command in the
benchmark guide. Results should be generated in a fresh output folder.
