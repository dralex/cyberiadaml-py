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
run as the binding's own suite runs them: from the parent of tests/, the
output compared with NN-output.txt.
"""
import pathlib
import runpy
import sys

import pytest
from cyberiadaml_py import cml

BINDING = pathlib.Path(__file__).resolve().parent / 'binding'
SCRIPTS = sorted(p.name for p in (BINDING / 'tests').glob('[0-9]*-*.py'))


@pytest.mark.parametrize('script', SCRIPTS)
def test_script(script, monkeypatch, capsys):
    """Check a binding test passes with the pure-Python interface."""
    monkeypatch.chdir(BINDING)
    monkeypatch.setitem(sys.modules, 'CyberiadaML', cml)
    monkeypatch.setattr(sys, 'argv', ['tests/' + script])
    with pytest.raises(SystemExit) as code:
        runpy.run_path('tests/' + script, run_name='__main__')
    out = capsys.readouterr()
    assert code.value.code in (0, None), out.err
    expected = BINDING / 'tests' / (script.split('-')[0] + '-output.txt')
    if expected.exists():
        assert out.out == expected.read_text(encoding='utf-8')
