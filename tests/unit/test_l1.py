# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The L1 layer tests: encoding, declaration, well-formedness
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
"""The L1 layer tests: encoding, declaration, well-formedness."""
from cyberiadaml_py.core import rules

from .docbuilder import DECLARATION, minimal


def run(data):
    """Return run."""
    return rules.run_document(data, 'test.graphml')


def rule_names(ctx):
    """Return rule names."""
    return [f.rule for f in ctx.report.findings]


def test_minimal_document_is_clean():
    """Check minimal document is clean."""
    ctx = run(minimal())
    assert ctx.report.findings == []
    assert ctx.report.verdict() == 'valid'
    assert 1 in ctx.report.layers_run
    assert ctx.parsed.root.tag == 'graphml'


def test_cyrillic_content_preserved():
    """Check cyrillic content preserved."""
    doc = minimal().replace(b'Test machine',
                            'Машина состояний'.encode('utf-8'))
    ctx = run(doc)
    assert ctx.report.findings == []
    text = [d.text for g in ctx.parsed.root.iter('graph')
            for d in g.findall('data')]
    assert 'Машина состояний' in text


def test_escaped_characters_unescaped_on_read():
    """Check escaped characters unescaped on read."""
    doc = minimal().replace(b'<data key="dName">Idle</data>',
                            b'<data key="dName">&quot;A&quot; &gt;= '
                            b'&amp; b</data>')
    ctx = run(doc)
    assert ctx.report.findings == []
    names = [d.text for n in ctx.parsed.root.iter('node')
             for d in n.findall('data') if d.get('key') == 'dName']
    assert '"A" >= & b' in names


def test_xml_comments_ignored():
    """Check xml comments ignored."""
    doc = minimal(
        gformat='<!-- top -->'
        '<data key="gFormat">Cyberiada-GraphML-1.0</data>\n')
    doc = doc.replace(b'<edge', b'<!-- between nodes and edges --><edge')
    doc = doc.replace(b'<node id="n0">', b'<node id="n0"><!-- inside node -->')
    ctx = run(doc)
    assert ctx.report.findings == []


def test_utf16_document_reported():
    """Check utf16 document reported."""
    text = minimal().decode('utf-8').replace('encoding="UTF-8"',
                                             'encoding="UTF-16"')
    ctx = run(text.encode('utf-16'))
    assert 'doc-encoding' in rule_names(ctx)
    assert ctx.report.has_warnings()
    assert not ctx.report.has_errors()
    assert not ctx.report.valid(strict=True)


def test_declared_non_utf8_encoding_reported():
    """Check declared non utf8 encoding reported."""
    ctx = run(minimal(
        declaration='<?xml version="1.0" encoding="windows-1251"?>\n'))
    assert 'doc-encoding' in rule_names(ctx)
    assert not ctx.report.has_errors()


def test_broken_utf8_reported():
    """Check broken utf8 reported."""
    ctx = run(minimal().replace(b'Idle', b'Idl\xff'))
    assert 'doc-encoding' in rule_names(ctx)


def test_missing_declaration_reported():
    """Check missing declaration reported."""
    ctx = run(minimal(declaration=''))
    assert rule_names(ctx) == ['xml-declaration']
    assert ctx.report.has_warnings()


def test_declaration_without_encoding_reported():
    """Check declaration without encoding reported."""
    ctx = run(minimal(declaration='<?xml version="1.0"?>\n'))
    assert rule_names(ctx) == ['xml-declaration']


def test_truncated_file_rejected():
    """Check truncated file rejected."""
    ctx = run(minimal()[:-40])
    findings = ctx.report.findings
    assert [f.rule for f in findings] == ['xml-well-formed']
    assert findings[0].line is not None
    assert ctx.report.verdict() == 'invalid'
    assert ctx.report.layers_run == [1]


def test_empty_file_rejected():
    """Check empty file rejected."""
    for data in (b'', b'   \n'):
        ctx = run(data)
        assert 'xml-not-empty' in rule_names(ctx)
        assert ctx.report.has_errors()


def test_binary_junk_rejected():
    """Check binary junk rejected."""
    ctx = run(bytes(range(256)))
    assert ctx.report.has_errors()
    assert ctx.parsed is None


def test_unescaped_ampersand_rejected():
    """Check unescaped ampersand rejected."""
    doc = minimal().replace(b'standardVersion/ 1.0', b'a && b')
    ctx = run(doc)
    errors = [f for f in ctx.report.findings if f.rule == 'xml-well-formed']
    assert errors and errors[0].line is not None


def test_registry_contains_l1_rules():
    """Check registry contains L1 rules."""
    rules.load_checks()
    for name in ('xml-well-formed', 'doc-encoding', 'char-escaping',
                 'data-escaping', 'xml-comments'):
        assert name in rules.REGISTRY
