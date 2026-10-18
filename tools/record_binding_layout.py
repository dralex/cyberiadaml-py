# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The geometry results of the CyberiadaML binding, recorded for the cml tests
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------
"""Record what the CyberiadaML binding does with the geometry of the examples.

    LD_LIBRARY_PATH=... PYTHONPATH=<binding build> \
        python3 tools/record_binding_layout.py

writes tests/cml/binding-layout.json: per example (tests/examples) the
results of the scenarios below - the dump of the document or the class of
the exception. tests/cml/test_layout.py runs the same with cml. Every
example runs in a process of its own: a crash of the binding loses one.
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / 'tests' / 'examples'
LAYOUT = ROOT / 'tests' / 'cml' / 'binding-layout.json'
FILE = re.compile(r", file: '[^']*'")


def _open(module, path: pathlib.Path):
    document = module.LocalDocument()
    document.open(str(path), module.formatDetect, module.geometryFormatQt)
    return document


def _dump(document) -> str:
    return FILE.sub('', repr(document))


def _saved(module, path: pathlib.Path) -> str:
    """Return the canonical dump of the rounded saved text."""
    sys.path.insert(0, str(ROOT))
    from cyberiadaml_py import core
    text = _open(module, path).encode(module.formatCyberiada10, True)
    return core.dump(core.read(text))


def _layout(module, path: pathlib.Path) -> str:
    document = _open(module, path)
    document.reconstruct_geometry(True)
    return _dump(document)


def _update(module, path: pathlib.Path) -> str:
    """Lay a new state and a transition to it into the layout."""
    document = _open(module, path)
    document.reconstruct_geometry(True)
    sm = document.get_state_machines()[0]
    states = [s for s in sm.get_children()
              if s.get_type() in (module.elementSimpleState,
                                  module.elementCompositeState)]
    added = document.new_state(sm, 'Added state')
    if states:
        document.new_transition(sm, module.transitionExternal, states[0],
                                added, module.Action('ADDED'))
    document.update_geometry(True)
    return _dump(document)


def _drawn(module, path: pathlib.Path) -> str:
    document = _open(module, path)
    document.update_geometry(True)
    return _dump(document)


SCENARIOS = {'qt': lambda m, p: _dump(_open(m, p)), 'saved': _saved,
             'layout': _layout, 'update': _update, 'drawn': _drawn}


def run(module, path: pathlib.Path) -> dict:
    """Return the result of every scenario: the dump or the exception."""
    result = {}
    for name, scenario in SCENARIOS.items():
        try:
            result[name] = scenario(module, path)
        except Exception as error:  # the binding registers them flat
            result[name] = 'EXC ' + type(error).__name__
    return result


def documents():
    """Return the examples: the standard ones and the Lapki corpus."""
    for folder in ('standard', 'lapki'):
        yield from sorted((EXAMPLES / folder).rglob('*.graphml'))


def main() -> int:
    """Record the results of the importable CyberiadaML module."""
    if len(sys.argv) == 2:
        import CyberiadaML  # type: ignore[import-not-found]
        print(json.dumps(run(CyberiadaML, pathlib.Path(sys.argv[1]))))
        return 0
    import CyberiadaML  # type: ignore[import-not-found]  # noqa: F811
    results = {}
    for path in documents():
        name = str(path.relative_to(EXAMPLES))
        child = subprocess.run([sys.executable, __file__, str(path)],
                               capture_output=True, text=True)
        if child.returncode:
            results[name] = {'crash': child.stderr.strip().splitlines()[-1:]}
        else:
            results[name] = json.loads(child.stdout)
    record = {'binding': getattr(CyberiadaML, '__version__', '?'),
              'documents': results}
    LAYOUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) +
                      '\n', encoding='utf-8')
    print('%d documents recorded' % len(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
