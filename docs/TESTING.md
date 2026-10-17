# cyberiadaml-py Testing

The tests check the library against the standard and the Lapki dialect through the documents of
cyberiadaml-compat-tests, against the producer side through documents written by cyberiadaml-js,
and against its users through the 1.x contract. Everything runs from the repository, without the
other checkouts: their documents are kept as snapshots with the revision they were taken from.

```
  cyberiadaml-compat-tests                            cyberiadaml-js (pinned version)
 +----------------------------------+                +----------------------------------+
 |  fixtures/ (standard)            |                |  tools/write-contract            |
 |  fixtures/dialect/lapki/         |                |  writes the examples back        |
 +----------------------------------+                +----------------------------------+
                  |                                                   |
                  | tools/sync_examples.py                            | js-written documents
                  v                                                   v
  tests/examples/standard/ ... /lapki/                  tests/examples/js-<version>/
                  |                                                   |
         +--------+--------+                                          |
         v                 v                                          v
  tests/conformance/   tests/dialect/                          tests/contract/
```

## Test layers

| directory | what | how |
|---|---|---|
| `tests/unit/` | behaviour grammar (§6.8), metadata (§6.9), escaping (§5.2), ids, writer order, findings | small inline documents |
| `tests/conformance/` | the standard examples | positive: strict read, dump equals `.expected.txt`; write, strict re-read, same dump. Negative: strict read raises `CGMLError` with the requirement id of the example; permissive read reports it |
| `tests/dialect/` | the Lapki corpus | permissive read: dump equals `.expected.txt`, repair findings equal `.repairs.txt`; strict read raises; the written document reads in strict mode |
| `tests/contract/` | documents written by cyberiadaml-js (`exportGraphml`) from the same examples | strict read, the dump equals the one cyberiadaml-js recorded for the written document; the 1.x parser reads it |
| `tests/legacy/` | the 1.x interface | the 1.4 tests; `lapki-compiler-view.json` — the fields lapki-compiler reads (`platform`, `meta.values`, states with `parent` and `actions`, transitions, vertices, components) for the 40 corpus documents, compared with cyberiadaml-py 1.4.1 when recorded (`python3 -m tests.legacy.test_contract`); the builder: standard output and the 1.x round trip; the 1.6 fields: every positive example and valid Lapki document through the parser and the builder gives the same dump (1.x-trimmed texts and component bodies normalised) |
| `tests/cml/` | the CyberiadaML interface | the libcyberiadamlpp-py tests of the provided tiers, ported with their numbers and inputs: the expected text of the dump as the binding gives it, the written documents compared by the canonical dump; the consumers (hsm-dispatcher-py, hsm-console-viewer, hsm_robot_ros_generator, cybersphere-agents `check`) give the same output with `cml` as with the binding |

The 1.4 test of the private `_split_graph` is replaced by the dialect tests of D-9.

## Examples

    python3 tools/sync_examples.py ~/sources/cyberiadaml-compat-tests

copies the standard examples, their manifest and the dialect corpus into `tests/examples/` and
writes the source revision to `tests/examples/REVISION`. A snapshot change is a commit of its
own; the differences of the expected dumps are reviewed in it. The examples keep the licences of
their sources, listed in `tests/examples/README.md`.

The js-written documents are produced in the cyberiadaml-js checkout of the pinned version:

    npm run build && node tools/write-contract.mjs ~/sources/cyberiadaml-py/tests/examples

writes `tests/examples/js-<version>/` with a `manifest.json` naming the cyberiadaml-js revision and
the examples it read.

The binding's view of the examples is recorded with the binding importable:

    LD_LIBRARY_PATH=<libs> PYTHONPATH=<binding build> python3 tools/record_binding_view.py

## Running

    poetry install
    poetry run pytest
    poetry run flake8 cyberiadaml_py tests
    poetry run mypy cyberiadaml_py tests

The GitHub workflows run the same three commands.

## Outside the repository

* the compatibility harness of cyberiadaml-compat-tests:
  `python3 -m intharness run --driver py`, then `report` - the profiles claimed by the driver and
  the interop with the other libraries;
* lapki-compiler: its `pytest` with this checkout installed - the compiled examples.
