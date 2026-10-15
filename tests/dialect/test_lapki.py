# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The Lapki dialect corpus read by the core
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
"""The Lapki dialect corpus read by the core."""
import collections
import json
import pathlib

import pytest
from cyberiadaml_py import core

CORPUS = pathlib.Path(__file__).resolve().parent.parent / 'examples' / \
    'lapki'
DOCUMENTS = json.loads((CORPUS / 'manifest.json')
                       .read_text(encoding='utf-8'))['documents']


def _data(name):
    return (CORPUS / (name + '.graphml')).read_bytes()


@pytest.mark.parametrize('name', sorted(DOCUMENTS))
def test_repairs(name):
    """Check the repairs of a corpus document."""
    document = core.read(_data(name))
    counts = collections.Counter(f.req for f in document.findings
                                 if f.layer == 0)
    text = ''.join('%s %d\n' % item for item in sorted(counts.items()))
    assert text == (CORPUS / (name + '.repairs.txt')).read_text(
        encoding='utf-8')
    assert document.label == core.FORMAT_LAPKI


@pytest.mark.parametrize('name', sorted(DOCUMENTS))
def test_result(name):
    """Check the dump of a valid document, the errors of an invalid one."""
    document = core.read(_data(name))
    entry = DOCUMENTS[name]
    errors = sorted({f.req or f.rule for f in document.findings
                     if f.severity == core.ERROR})
    if entry['status'] == 'valid':
        assert errors == []
        assert core.dump(document) == (
            CORPUS / (name + '.expected.txt')).read_text(encoding='utf-8')
    else:
        assert errors == entry['errors']


@pytest.mark.parametrize('name', sorted(DOCUMENTS))
def test_strict_read_rejects(name):
    """Check the strict read rejects a dialect document."""
    with pytest.raises(core.CGMLError):
        core.read(_data(name), strict=True)
