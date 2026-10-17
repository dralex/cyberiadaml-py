# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The libcyberiadamlpp-py tests run with the pure-Python interface
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
"""The libcyberiadamlpp-py tests run with cml as CyberiadaML.

The scripts and their documents are copies (binding/tests, REVISION); they
run as the binding's own suite runs them: from the parent of tests/ (a
scratch copy, the scripts write their documents there), the output compared
with NN-output.txt, the written document with NN-output.graphml by the
canonical dump (the writers differ in bytes).
"""
import pathlib
import runpy
import shutil
import sys

import pytest
from cyberiadaml_py import cml, core

BINDING = pathlib.Path(__file__).resolve().parent / 'binding'
SCRIPTS = sorted(p.name for p in (BINDING / 'tests').glob('[0-9]*-*.py'))


def _dump(path: pathlib.Path) -> str:
    return core.dump(core.read(path.read_text(encoding='utf-8')))


@pytest.mark.parametrize('script', SCRIPTS)
def test_script(script, tmp_path, monkeypatch, capsys):
    """Check a binding test passes with the pure-Python interface."""
    shutil.copytree(BINDING / 'tests', tmp_path / 'tests')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, 'CyberiadaML', cml)
    monkeypatch.setattr(sys, 'argv', ['tests/' + script])
    try:
        runpy.run_path('tests/' + script, run_name='__main__')
        status = None
    except SystemExit as stop:
        status = stop.code
    out = capsys.readouterr()
    assert status in (0, None), out.err
    number = script.split('-')[0]
    expected = BINDING / 'tests' / (number + '-output.txt')
    if expected.exists():
        assert out.out == expected.read_text(encoding='utf-8')
    expected = BINDING / 'tests' / (number + '-output.graphml')
    if expected.exists():
        written = tmp_path / 'tests' / (script + '.graphml')
        assert _dump(written) == _dump(expected)
