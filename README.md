# The Cyberiada State Machine Python 3 Library

The native Python 3 library for processing CyberiadaML - the version of GraphML for storing state machine graphs
used by the Cyberiada Project. 

The code is distributed under the Lesser GNU Public License (version 3), the documentation -- under
the GNU Free Documentation License (version 1.3).

## Documentation

The documentation is located in the `docs` directory and contains:

* The architecture - `ARCHITECTURE.md`
* The interface specification - `API.md`
* The CyberiadaML interface - `CML.md`
* The testing - `TESTING.md`

## Usage

The standard-compliant core reads standard documents and, in the permissive mode, the
pre-standard Lapki dialect:

    from cyberiadaml_py import core

    document = core.read(text)                 # core.read(text, strict=True)
    print(document.label, document.findings)
    text = core.write(document)                # a standard document
    print(core.dump(document))                 # the canonical dump

The 1.x interface (`CGMLParser`, `CGMLBuilder`) stays as it was.

## Tests

    python3 -m pytest
    flake8 cyberiadaml_py tests
    mypy cyberiadaml_py && mypy tests

The tests read the conformance examples and the Lapki dialect corpus kept in `tests/examples`
(see `docs/TESTING.md`).

## Requirements

* Python 3.8.1 or newer - the core uses the standard library only
* `pydantic` (2.6+; 2.10 is the last for Python 3.8) - the 1.x types
* `poetry` - the development environment with the test and lint tools
* `cmake` (version 3.16+) - for the Debian package

## Installation

With pip (PyPI, a virtual environment, Windows, macOS):

    pip install cyberiadaml-py

The Debian package `python3-cyberiadaml` installs the library into the system Python:

    cmake -B build && cd build && ctest && cpack -G DEB
    sudo apt install ./python3-cyberiadaml_1.8.0_all.deb

`ctest` runs the tests with the Python CMake finds; it needs pytest and pydantic
(`-DPython3_EXECUTABLE=...` selects another one).

**Github: https://github.com/kruzhok-team/cyberiadaml-py**
