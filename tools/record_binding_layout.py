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

    ... python3 tools/record_binding_layout.py --arrange

writes tests/cml/binding-arrange.json with the scenarios `layout` and
`arranged` alone, for tests/cml/test_arrange.py: the arrange needs a binding
of libcyberiadamlpp 1.1, whose full layout is newer than the one recorded in
binding-layout.json.
"""
import json
import pathlib
import re
import subprocess
import sys
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / 'tests' / 'examples'
LAYOUT = ROOT / 'tests' / 'cml' / 'binding-layout.json'
ARRANGE = ROOT / 'tests' / 'cml' / 'binding-arrange.json'
ARRANGE_FLAG = '--arrange'
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


def _arranged(module, path: pathlib.Path) -> str:
    """Lay the document out anew as its drawing arranges it."""
    document = _open(module, path)
    document.arrange_geometry(True)
    return _dump(document)


SCENARIOS = {'qt': lambda m, p: _dump(_open(m, p)), 'saved': _saved,
             'layout': _layout, 'update': _update, 'drawn': _drawn}
ARRANGE_SCENARIOS = {'layout': _layout, 'arranged': _arranged}


def run(module, path: pathlib.Path, scenarios: Optional[dict] = None) -> dict:
    """Return the result of every scenario: the dump or the exception."""
    result = {}
    for name, scenario in (scenarios or SCENARIOS).items():
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
    args = sys.argv[1:]
    arrange = ARRANGE_FLAG in args
    args = [a for a in args if a != ARRANGE_FLAG]
    scenarios = ARRANGE_SCENARIOS if arrange else SCENARIOS
    if len(args) == 1:
        import CyberiadaML  # type: ignore[import-not-found]
        print(json.dumps(run(CyberiadaML, pathlib.Path(args[0]), scenarios)))
        return 0
    import CyberiadaML  # type: ignore[import-not-found]  # noqa: F811
    results = {}
    for path in documents():
        name = str(path.relative_to(EXAMPLES))
        child = subprocess.run([sys.executable, __file__, str(path)] +
                               ([ARRANGE_FLAG] if arrange else []),
                               capture_output=True, text=True)
        if child.returncode:
            results[name] = {'crash': child.stderr.strip().splitlines()[-1:]}
        else:
            results[name] = json.loads(child.stdout)
    record = {'binding': getattr(CyberiadaML, '__version__', '?'),
              'documents': results}
    (ARRANGE if arrange else LAYOUT).write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + '\n',
        encoding='utf-8')
    print('%d documents recorded' % len(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
