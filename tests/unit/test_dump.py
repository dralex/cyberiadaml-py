# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The canonical dump tests
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
"""The canonical dump tests."""
import pathlib

import pytest
from cyberiadaml_py.core import rules
from cyberiadaml_py.core.dump import render

from .docbuilder import minimal

EXAMPLES = pathlib.Path(__file__).parent / 'examples'


def validated(data, filename='test.graphml'):
    """Return validated."""
    ctx = rules.run_document(data, filename)
    assert not ctx.report.has_errors(), \
        [f.rule for f in ctx.report.findings]
    return ctx


def expected(name):
    """Return expected."""
    return (EXAMPLES / name).read_text(encoding='utf-8')


@pytest.mark.parametrize('name', ['minimal', 'hierarchy', 'extensions'])
def test_dump_matches_expected(name):
    """Check dump matches expected."""
    path = EXAMPLES / (name + '.graphml')
    ctx = validated(path.read_bytes(), str(path))
    assert ctx.report.findings == []
    assert render(ctx.model) == expected(name + '.expected.txt')


def test_dump_deterministic():
    """Check dump deterministic."""
    path = EXAMPLES / 'hierarchy.graphml'
    first = validated(path.read_bytes())
    second = validated(path.read_bytes())
    assert render(first.model) == render(second.model)
    assert render(first.model) == render(first.model)


def test_default_and_declared_key_twins_dump_identically():
    """Check default and declared key twins dump identically."""
    declared = validated(minimal())
    defaults = validated(minimal(keys=''))
    assert render(declared.model) == render(defaults.model)
