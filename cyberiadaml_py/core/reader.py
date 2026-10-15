# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The reader: the validation layers, the dialect pass and the reading modes
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
"""The reader: the validation layers, the dialect pass and the modes."""
from typing import List, Union

from . import dialect, model, rules, tagtree, xmlload
from .findings import ERROR, Finding, Report
from .keys import STANDARD_KEY_IDS
from .model import Document, Extension
from .rules import declare

declare('document-model', None, 2, ERROR,
        'the document holds a state machine graph to read')

# findings that leave no model to read, in either mode
FATAL_RULES = frozenset(('xml-not-empty', 'xml-well-formed', 'element-ids',
                         'unique-ids', 'document-model'))
DOCUMENT_NAME = '<document>'


class CGMLError(Exception):
    """The document cannot be read; findings tell why."""

    def __init__(self, findings: List[Finding]) -> None:
        self.findings = list(findings)
        first = [f for f in self.findings if f.rule in FATAL_RULES] or \
            [f for f in self.findings if f.severity == ERROR] or \
            self.findings
        super().__init__(first[0].render(DOCUMENT_NAME) if first
                         else 'the document cannot be read')


def _stop(ctx: rules.Context, strict: bool, layer: int) -> None:
    fatal = [f for f in ctx.report.findings if f.rule in FATAL_RULES]
    if fatal or (strict and ctx.report.has_errors(layer=layer)):
        raise CGMLError(ctx.report.findings)


def _line(ctx: rules.Context, elem: object) -> Union[int, None]:
    info = ctx.parsed.info.get(elem)
    return info[0] if info else None


def _extensions(elem) -> list:
    return [Extension(d.get('key'), d.text, d) for d in elem
            if d.tag == 'data' and d.get('key') not in STANDARD_KEY_IDS]


def _annotate(ctx: rules.Context, item, parent) -> None:
    item.parent = parent
    item.line = _line(ctx, item.elem)
    item.extensions = _extensions(item.elem)
    for region in getattr(item, 'regions', []):
        _annotate(ctx, region, item)
    for child in getattr(item, 'children', []):
        _annotate(ctx, child, item)


def _finish(ctx: rules.Context) -> Document:
    document = ctx.model
    document.findings = ctx.report.findings
    result = ctx.dialect
    if result is not None:
        document.label = result.label
        document.extension_graphs = result.extension_graphs
    for machine in document.machines:
        machine.line = _line(ctx, machine.elem)
        machine.extensions = _extensions(machine.elem)
        if result is not None:
            machine.params = result.machine_params.get(machine.id, [])
        for child in machine.children:
            _annotate(ctx, child, machine)
        for edge in machine.transitions + machine.links:
            _annotate(ctx, edge, machine)
    return document


def read(data: Union[str, bytes], *, strict: bool = False) -> Document:
    """Read a document; raise CGMLError when it cannot be read.

    Strict: the standard alone, the first layer with an ERROR stops the
    reading. Permissive: the Lapki dialect is repaired first, the ERROR
    findings stay in Document.findings, only the fatal ones raise.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    rules.load_checks()
    ctx = rules.Context(Report(), DOCUMENT_NAME)
    ctx.layer = 1
    ctx.parsed = xmlload.load(data, ctx)
    ctx.report.layers_run.append(1)
    if ctx.parsed is None:
        raise CGMLError(ctx.report.findings)
    _stop(ctx, strict, 1)
    if not strict:
        ctx.layer = 0
        ctx.dialect = dialect.apply(ctx)
    ctx.layer = 2
    tagtree.check(ctx)
    ctx.report.layers_run.append(2)
    if ctx.parsed.root.tag != 'graphml':
        raise CGMLError(ctx.report.findings)
    _stop(ctx, strict, 2)
    ctx.model = model.build(ctx.parsed)
    for layer in (3, 4):
        rules.run_layer(ctx, layer)
        _stop(ctx, strict, layer)
    if not ctx.model.machines:
        ctx.emit('document-model', 'no state machine graph to read',
                 elem=ctx.parsed.root)
        raise CGMLError(ctx.report.findings)
    return _finish(ctx)
