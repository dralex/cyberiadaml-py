# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The conformance examples of the standard read by the core
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
"""The conformance examples of the standard read by the core."""
import json
import pathlib

import pytest
from cyberiadaml_py import core
from cyberiadaml_py.core.rules import REGISTRY

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / 'examples' / \
    'standard'
MANIFEST = json.loads((EXAMPLES / 'manifest.json')
                      .read_text(encoding='utf-8'))['fixtures']
POSITIVE = sorted(n for n, e in MANIFEST.items() if 'reject' not in e)
NEGATIVE = sorted(n for n, e in MANIFEST.items() if 'reject' in e)


def _data(name):
    return (EXAMPLES / (name + '.graphml')).read_bytes()


def _cited(findings):
    """Return the requirement ids the findings report."""
    ids = set()
    for finding in findings:
        ids.add(finding.req)
        ids.update(REGISTRY[finding.rule].also)
    return ids


@pytest.mark.parametrize('name', POSITIVE)
def test_positive_strict_read(name):
    """Check a positive example reads strictly to its canonical dump."""
    document = core.read(_data(name), strict=True)
    expected = (EXAMPLES / (name + '.expected.txt')).read_text(
        encoding='utf-8')
    assert core.dump(document) == expected
    assert document.label == core.FORMAT_STANDARD


@pytest.mark.parametrize('name', POSITIVE)
def test_positive_permissive_read(name):
    """Check the permissive read of a positive example: no repair."""
    document = core.read(_data(name))
    assert [f for f in document.findings if f.layer == 0] == []
    assert not [f for f in document.findings if f.severity == core.ERROR]


@pytest.mark.parametrize('name', NEGATIVE)
def test_negative_strict_read_rejects(name):
    """Check a negative example is rejected with its requirement."""
    with pytest.raises(core.CGMLError) as error:
        core.read(_data(name), strict=True)
    assert MANIFEST[name]['reject'] in _cited(error.value.findings)


@pytest.mark.parametrize('name', NEGATIVE)
def test_negative_permissive_read_reports(name):
    """Check a permissive read reports, rejects or repairs the fault."""
    try:
        findings = core.read(_data(name)).findings
    except core.CGMLError as error:
        findings = error.findings
    repaired = [f for f in findings if f.layer == 0]
    assert repaired or MANIFEST[name]['reject'] in _cited(findings)
