# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The canonical dump writer
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
"""The canonical dump writer."""
from .model import (META_NAME, Comment, Point, Rect, State,
                    SubmachineState, Vertex)

HEADER = 'cgml-canonical-dump 1'
INDENT = '  '


def _quote(text):
    out = ['"']
    for char in text:
        if char == '\\':
            out.append('\\\\')
        elif char == '"':
            out.append('\\"')
        elif char == '\n':
            out.append('\\n')
        elif char == '\t':
            out.append('\\t')
        elif char == '\r':
            out.append('\\r')
        elif ord(char) < 32:
            out.append('\\u%04x' % ord(char))
        else:
            out.append(char)
    out.append('"')
    return ''.join(out)


def _num(value):
    text = '%.2f' % value
    return '0.00' if text == '-0.00' else text


def _geometry_text(obj):
    if isinstance(obj, Rect):
        return 'rect %s %s %s %s' % (_num(obj.x), _num(obj.y),
                                     _num(obj.width), _num(obj.height))
    return 'point %s %s' % (_num(obj.x), _num(obj.y))


def _sorted(items):
    return sorted(items, key=lambda item: item.id or '')


def _sorted_edges(items):
    return sorted(items,
                  key=lambda e: (e.source or '', e.target or '', e.id or ''))


class _Writer:

    def __init__(self):
        self.lines = [HEADER]

    def put(self, depth, text):
        self.lines.append(INDENT * depth + text)

    def text(self):
        return '\n'.join(self.lines) + '\n'


def _put_common(out, depth, node):
    if node.name:
        out.put(depth, 'name: %s' % _quote(node.name))
    if getattr(node, 'formal_name', None):
        out.put(depth, 'formal-name: %s' % _quote(node.formal_name))


def _put_block(out, depth, block):
    if block.kind == 'event':
        head = 'action event %s' % _quote(block.trigger)
        if block.param:
            head += ' ' + block.param
        if block.guard is not None:
            escaped = block.guard.replace('[', '\\[').replace(']', '\\]') \
                if block.guard != 'else' else 'else'
            head += ' guard %s' % _quote(escaped)
    else:
        head = 'action %s' % block.kind
    out.put(depth, head + ':')
    for line in block.behaviour:
        out.put(depth + 1, 'do: %s' % _quote(line))


def _put_trailer(out, depth, node):
    if node.geometry is not None:
        out.put(depth, 'geometry: %s' % _geometry_text(node.geometry))
    if getattr(node, 'color', None):
        out.put(depth, 'color: %s' % _quote(node.color))


def _put_region(out, depth, document, region):
    out.put(depth, 'region %s:' % _quote(region.id or ''))
    if region.name:
        out.put(depth + 1, 'name: %s' % _quote(region.name))
    if region.formal_name:
        out.put(depth + 1, 'formal-name: %s' % _quote(region.formal_name))
    if region.geometry is not None:
        out.put(depth + 1, 'geometry: %s' % _geometry_text(region.geometry))
    for child in _sorted(region.children):
        _put_node(out, depth + 1, document, child)


def _put_node(out, depth, document, node):
    quoted = _quote(node.id or '')
    if isinstance(node, Comment):
        out.put(depth, 'comment %s %s:' % (quoted, node.kind))
        _put_common(out, depth + 1, node)
        if node.kind == 'informal':
            out.put(depth + 1, 'markup: %s' %
                    _quote(node.markup or document.markup_language()))
        elif node.markup:              # a formal comment has no default
            out.put(depth + 1, 'markup: %s' % _quote(node.markup))
        if node.body is not None and \
                not (node.kind == 'formal' and node.name == META_NAME):
            # the metadata parameters are rendered by the meta section
            out.put(depth + 1, 'body: %s' % _quote(node.body))
        _put_trailer(out, depth + 1, node)
    elif isinstance(node, Vertex):
        out.put(depth, 'vertex %s %s:' % (quoted, node.kind))
        _put_common(out, depth + 1, node)
        _put_trailer(out, depth + 1, node)
    elif isinstance(node, SubmachineState):
        out.put(depth, 'submachine %s ref %s:' %
                (quoted, _quote(node.ref or '')))
        _put_common(out, depth + 1, node)
        _put_trailer(out, depth + 1, node)
        for region in _sorted(node.regions):
            _put_region(out, depth + 1, document, region)
    elif isinstance(node, State):
        out.put(depth, 'state %s:' % quoted)
        _put_common(out, depth + 1, node)
        if node.collapsed:
            out.put(depth + 1, 'collapsed')
        for block in node.blocks:
            _put_block(out, depth + 1, block)
        _put_trailer(out, depth + 1, node)
        for region in _sorted(node.regions):
            _put_region(out, depth + 1, document, region)


def _put_transition(out, depth, transition):
    out.put(depth, 'transition %s: %s -> %s' %
            (_quote(transition.id or ''), _quote(transition.source or ''),
             _quote(transition.target or '')))
    for block in transition.blocks:
        _put_block(out, depth + 1, block)
    if transition.polyline:
        out.put(depth + 1, 'polyline: %s' %
                ' '.join(_geometry_text(p) for p in transition.polyline))
    if transition.source_point is not None:
        out.put(depth + 1, 'source-point: %s' %
                _geometry_text(transition.source_point))
    if transition.target_point is not None:
        out.put(depth + 1, 'target-point: %s' %
                _geometry_text(transition.target_point))
    if transition.label_geometry is not None:
        out.put(depth + 1, 'label-geometry: %s' %
                _geometry_text(transition.label_geometry))
    if transition.color:
        out.put(depth + 1, 'color: %s' % _quote(transition.color))


def _put_link(out, depth, link):
    line = 'comment-link %s: %s -> %s pivot %s' % (
        _quote(link.id or ''), _quote(link.source or ''),
        _quote(link.target or ''), _quote(link.pivot or ''))
    if link.chunk is not None:
        line += ' chunk %s' % _quote(link.chunk)
    out.put(depth, line)


def render(document):
    """Render the canonical dump of a validated document model."""
    out = _Writer()
    out.put(0, 'format: %s' % _quote(document.format or ''))
    out.put(0, 'geometry-mode: %s' % document.geometry_mode)
    out.put(0, 'transition-order: %s' % document.transition_order())
    out.put(0, 'event-propagation: %s' % document.event_propagation())
    if document.meta_params:
        out.put(0, 'meta:')
        for par in sorted(document.meta_params,
                          key=lambda p: (p.name != 'standardVersion', p.name)):
            out.put(1, 'param %s: %s' % (_quote(par.name), _quote(par.value)))
    for machine in _sorted(document.machines):
        out.put(0, 'state-machine %s:' % _quote(machine.id or ''))
        _put_common(out, 1, machine)
        if machine.geometry is not None:
            out.put(1, 'geometry: %s' % _geometry_text(machine.geometry))
        for child in _sorted(machine.children):
            _put_node(out, 1, document, child)
        for transition in _sorted_edges(machine.transitions):
            _put_transition(out, 1, transition)
        for link in _sorted_edges(machine.links):
            _put_link(out, 1, link)
    return out.text()
