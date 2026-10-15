# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The L3 layer: attribute and value checks
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
"""The L3 layer: attribute and value checks."""
import datetime
import re

from . import model as model_mod
from .findings import ERROR, INFO, WARNING
from .keys import (CSS_COLOR_NAMES, EVENT_PROPAGATIONS, GEOMETRY_MODES,
                   NOTE_KINDS, STANDARD_BINDINGS, STANDARD_KEY_IDS,
                   TRANSITION_ORDERS, UNTYPED_KEYS, VERTEX_CORE,
                   VERTEX_EXT, VERTEX_RESERVED)
from . import meta
from .rules import declare, rule

FORMAT_VALUE = 'Cyberiada-GraphML-1.0'

ID_EXCLUDED = frozenset('"\'`\\')
ID_MAX_LENGTH = 256

FORMAL_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$')
LATIN_NAME_RE = re.compile(r'^[A-Za-z]+$')
HEX_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$')
EDGE_ID_RE = re.compile(r'^.+-.+(#[0-9]+)?$')
PIVOT_VALUES = ('dName', 'dData', '')
COMPONENT_PREFIX = model_mod.COMPONENT_NAME + ' '

declare('key-defaults', 'CGML-5.5-2', 3, INFO,
        'the appendix B defaults apply when the key block is absent',
        note='the model applies the default declarations')
declare('behaviour-blocks', 'CGML-6.8-2', 3, INFO,
        'behaviour blocks are separated by blank lines',
        note='checked by the behaviour parser')
declare('behaviour-keywords', 'CGML-6.8-3', 3, INFO,
        'entry/, exit/ and do/ blocks are recognized',
        note='checked by the behaviour parser')
declare('event-name', 'CGML-6.8-4', 3, INFO,
        'the event description begins with the event name',
        note='checked by the behaviour parser')
declare('event-params', 'CGML-6.8-5', 3, INFO,
        'the propagate, block and defer event parameters are recognized',
        note='checked by the behaviour parser')
declare('behaviour-block-once', 'CGML-6.8-3-1', 3, ERROR,
        'a state carries at most one entry/, exit/ and do/ block')
declare('event-name-reserved', 'CGML-6.8-4-1', 3, ERROR,
        'event names are not reserved words')
declare('defer-usage', 'CGML-6.8-5-1', 3, ERROR,
        'defer is the whole behaviour of an internal transition')
declare('param-needs-event', 'CGML-6.8-5-2', 3, ERROR,
        'propagate and block require an event name')
declare('else-guard', 'CGML-6.8-6', 3, INFO,
        'the else guard keyword is recognized',
        note='checked by the behaviour parser')
declare('guard-brackets', 'CGML-6.8-8', 3, INFO,
        'escaped square brackets in guards are recognized',
        note='checked by the behaviour parser')
declare('meta-text-params', 'CGML-6.9-4-2', 3, INFO,
        'the standard text parameters are preserved',
        note='values are kept in the model')
declare('markup-default', 'CGML-6.9-4-6', 3, INFO,
        'the markupLanguage parameter sets the comment markup default',
        note='resolved by the model')
declare('custom-params', 'CGML-6.9-5', 3, INFO,
        'additional metadata parameters are preserved',
        note='values are kept in the model')


_elements = model_mod.iter_elements


def _all_data(root):
    for elem in root.iter('data'):
        yield elem


@rule('gformat-value', 'CGML-5.4-2', 3, ERROR,
      'the gFormat value is "%s"' % FORMAT_VALUE)
def _gformat_value(ctx):
    doc = ctx.model
    if doc.format_elem is None:
        return
    if (doc.format or '').strip() != FORMAT_VALUE:
        ctx.emit('gformat-value',
                 'the gFormat value is %r, expected "%s"' %
                 (doc.format, FORMAT_VALUE), elem=doc.format_elem)


@rule('key-declarations', 'CGML-appendix-B-1', 3, ERROR,
      'key declarations agree with the appendix B inventory')
def _key_declarations(ctx):
    doc = ctx.model
    declared = set()
    for decl in doc.keys:
        declared.add(decl.id)
        if decl.id not in STANDARD_KEY_IDS:
            continue
        binding = STANDARD_BINDINGS.get((decl.id, decl.for_kind))
        if binding is None:
            ctx.emit('key-declarations',
                     'standard key %s redeclared for %r' %
                     (decl.id, decl.for_kind), elem=decl.elem)
        elif decl.attr_name is not None and decl.attr_name != binding:
            ctx.emit('key-declarations',
                     'standard key %s redeclared with attr.name %r, '
                     'expected %r' % (decl.id, decl.attr_name, binding),
                     elem=decl.elem)
    for data in _all_data(doc.root):
        key = data.get('key')
        if key is not None and key not in STANDARD_KEY_IDS \
                and key not in declared:
            ctx.emit('key-declarations',
                     'data key %s is neither standard nor declared' % key,
                     elem=data)


@rule('key-type', 'CGML-5.5-5', 3, ERROR,
      'standard key declarations keep the appendix B attr.type')
def _key_type(ctx):
    for decl in ctx.model.keys:
        if decl.id not in STANDARD_KEY_IDS or decl.attr_type is None:
            continue
        if decl.id in UNTYPED_KEYS:
            ctx.emit('key-type',
                     'standard key %s declared with attr.type %r; appendix B '
                     'declares no type' % (decl.id, decl.attr_type),
                     elem=decl.elem)
        elif decl.attr_type != 'string':
            ctx.emit('key-type',
                     'standard key %s declared with attr.type %r, expected '
                     '"string"' % (decl.id, decl.attr_type), elem=decl.elem)


@rule('data-key-attr', 'CGML-5.5-3', 3, ERROR,
      'every data tag carries a key attribute')
def _data_key_attr(ctx):
    for data in _all_data(ctx.model.root):
        if data.get('key') is None:
            ctx.emit('data-key-attr', 'data tag without a key attribute',
                     elem=data)


@rule('element-ids', 'CGML-5.9-1', 3, ERROR,
      'every graph, node and edge carries an id')
def _element_ids(ctx):
    for kind, elem in _elements(ctx.model.root):
        if elem.get('id') is None:
            ctx.emit('element-ids', '%s without an id attribute' % kind,
                     elem=elem)


@rule('id-charset', 'CGML-5.9-2', 3, ERROR,
      'ids use ASCII 33-126 except quotes, the backquote and the backslash')
def _id_charset(ctx):
    for kind, elem in _elements(ctx.model.root):
        value = elem.get('id')
        if not value:
            continue
        for char in value:
            if not 33 <= ord(char) <= 126 or char in ID_EXCLUDED:
                ctx.emit('id-charset',
                         '%s id %r contains the inadmissible character %r' %
                         (kind, value, char), elem=elem)
                break


@rule('id-length', 'CGML-5.9-3', 3, ERROR,
      'ids are non-empty and at most 256 characters long')
def _id_length(ctx):
    for kind, elem in _elements(ctx.model.root):
        value = elem.get('id')
        if value is None:
            continue
        if not value:
            ctx.emit('id-length', '%s with an empty id' % kind, elem=elem)
        elif len(value) > ID_MAX_LENGTH:
            ctx.emit('id-length',
                     '%s id is %d characters long, at most %d allowed' %
                     (kind, len(value), ID_MAX_LENGTH), elem=elem)


@rule('edgedefault', 'CGML-5.6-1', 3, WARNING,
      'graphs carry edgedefault="directed"')
def _edgedefault(ctx):
    for machine in ctx.model.machines:
        value = machine.elem.get('edgedefault')
        if value != 'directed':
            ctx.emit('edgedefault',
                     'graph edgedefault is %r, expected "directed"' % value,
                     elem=machine.elem)
    # regions carry no edges; only an explicit wrong value is reported
    for region in model_mod.iter_regions(ctx.model):
        value = region.elem.get('edgedefault')
        if value is not None and value != 'directed':
            ctx.emit('edgedefault',
                     'region edgedefault is %r, expected "directed"' %
                     value, elem=region.elem)


@rule('edge-endpoints', 'CGML-5.8-1', 3, ERROR,
      'edges carry non-empty source and target attributes')
def _edge_endpoints(ctx):
    for kind, elem in _elements(ctx.model.root):
        if kind != 'edge':
            continue
        for name in ('source', 'target'):
            if not elem.get(name):
                ctx.emit('edge-endpoints',
                         'edge without a non-empty %s attribute' % name,
                         elem=elem)


@rule('edge-id-template', 'CGML-5.8-2', 3, INFO,
      'edge ids follow the source-target or source-target#N template')
def _edge_id_template(ctx):
    for kind, elem in _elements(ctx.model.root):
        if kind != 'edge':
            continue
        value = elem.get('id')
        if value and not EDGE_ID_RE.match(value):
            ctx.emit('edge-id-template',
                     'edge id %r does not follow the source-target[#N] '
                     'template' % value, elem=elem)


@rule('sm-marker-value', 'CGML-6.1-1', 3, ERROR,
      'the dStateMachine marker value is empty')
def _sm_marker_value(ctx):
    for machine in ctx.model.machines:
        value = model_mod.data_value(machine.elem, 'dStateMachine')
        if value and value.strip():
            ctx.emit('sm-marker-value',
                     'dStateMachine carries the non-empty value %r' % value,
                     elem=machine.elem)


@rule('marker-values', 'CGML-6.5-2', 3, WARNING,
      'the dRegion and dCollapsed marker values are empty')
def _marker_values(ctx):
    for data in _all_data(ctx.model.root):
        if data.get('key') in ('dRegion', 'dCollapsed') \
                and data.text and data.text.strip():
            ctx.emit('marker-values',
                     '%s carries the non-empty value %r' %
                     (data.get('key'), data.text), elem=data)


@rule('vertex-value', 'CGML-6.4-2', 3, ERROR,
      "dVertex values come from the standard's table 3")
def _vertex_value(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        if not isinstance(node, model_mod.Vertex):
            continue
        kind = (node.kind or '').strip()
        if kind in VERTEX_RESERVED:
            ctx.emit('vertex-reserved',
                     'dVertex value %r is reserved; tolerated on read as an '
                     'unknown vertex' % kind, elem=node.elem)
        elif kind not in VERTEX_CORE + VERTEX_EXT:
            ctx.emit('vertex-value',
                     'dVertex value %r is not admissible' % kind,
                     elem=node.elem)


declare('vertex-reserved', 'CGML-6.4-2', 3, WARNING,
        'the reserved fork and join vertexes are tolerated on read')


@rule('note-value', 'CGML-6.6-1', 3, ERROR,
      'dNote values are informal or formal')
def _note_value(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        if isinstance(node, model_mod.Comment) \
                and (node.kind or '').strip() not in NOTE_KINDS:
            ctx.emit('note-value',
                     'dNote value %r is not admissible' % node.kind,
                     elem=node.elem)


@rule('color-value', 'CGML-9.2-2', 3, ERROR,
      'dColor values are #RRGGBB, #RRGGBBAA or a CSS colour name',
      also=('CGML-9.2-1', 'CGML-9.2-3'))
def _color_value(ctx):
    for data in _all_data(ctx.model.root):
        if data.get('key') != 'dColor':
            continue
        value = (data.text or '').strip()
        if not value:
            ctx.emit('color-value', 'empty dColor value', elem=data)
        elif value.startswith('#'):
            if not HEX_COLOR_RE.match(value):
                ctx.emit('color-value',
                         'dColor value %r is not a #RRGGBB or #RRGGBBAA '
                         'color' % value, elem=data)
        elif value.lower() not in CSS_COLOR_NAMES:
            ctx.emit('color-value',
                     'dColor value %r is neither a #RRGGBB[AA] color nor a '
                     'CSS colour name' % value, elem=data)


@rule('markup-usage', 'CGML-9.3-2', 3, ERROR,
      'dMarkup appears on comments only, with a non-empty value',
      also=('CGML-9.3-1',))
def _markup_usage(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        markup = model_mod.data_value(node.elem, 'dMarkup')
        if markup is None:
            continue
        if not isinstance(node, model_mod.Comment):
            ctx.emit('markup-usage',
                     'dMarkup on a node that is not a comment',
                     elem=node.elem)
        elif not markup.strip():
            ctx.emit('markup-usage', 'empty dMarkup value', elem=node.elem)


@rule('formal-name-syntax', 'CGML-10.1-2', 3, ERROR,
      'formal names are identifiers of latin letters, digits and underscores')
def _formal_name_syntax(ctx):
    for data in _all_data(ctx.model.root):
        if data.get('key') != 'dFormalName':
            continue
        value = data.text or ''
        if not FORMAL_NAME_RE.match(value):
            ctx.emit('formal-name-syntax',
                     'formal name %r does not match the identifier syntax' %
                     value, elem=data)


@rule('pivot-value', 'CGML-6.7-1', 3, ERROR,
      'dPivot names dName, dData or is empty')
def _pivot_value(ctx):
    for machine in ctx.model.machines:
        for link in machine.links:
            if (link.pivot or '').strip() not in PIVOT_VALUES:
                ctx.emit('pivot-value',
                         'dPivot value %r is not admissible' % link.pivot,
                         elem=link.elem)


@rule('chunk-required', 'CGML-6.7-3', 3, ERROR,
      'a dName or dData link carries a non-empty dChunk')
def _chunk_required(ctx):
    for machine in ctx.model.machines:
        for link in machine.links:
            if (link.pivot or '').strip() in ('dName', 'dData') \
                    and not (link.chunk or '').strip():
                ctx.emit('chunk-required',
                         'comment link with dPivot %r carries no non-empty '
                         'dChunk' % link.pivot, elem=link.elem)


@rule('chunk-no-target-point', 'CGML-9.1-1-3-4', 3, ERROR,
      'a link to a subject aspect carries no dTargetPoint')
def _chunk_no_target_point(ctx):
    for machine in ctx.model.machines:
        for link in machine.links:
            target_point = model_mod.data_value(link.elem, 'dTargetPoint')
            if link.chunk is not None and target_point is not None:
                ctx.emit('chunk-no-target-point',
                         'comment link with dChunk carries a dTargetPoint',
                         elem=link.elem)


@rule('component-syntax', 'CGML-10.3-1', 3, ERROR,
      'CGML_COMPONENT comments name a component unique in its state machine '
      'and its type')
def _component_syntax(ctx):
    for machine in ctx.model.machines:
        # the component identifier is unique in its machine; the node ids are
        # unique in the whole document (CGML-5.9-4)
        seen = {}
        for node in model_mod.iter_machine_nodes(machine):
            if not isinstance(node, model_mod.Comment) \
                    or (node.kind or '').strip() != 'formal':
                continue
            name = node.name or ''
            if name != model_mod.COMPONENT_NAME \
                    and not name.startswith(COMPONENT_PREFIX):
                continue
            ident = name[len(COMPONENT_PREFIX):]
            if not FORMAL_NAME_RE.match(ident):
                ctx.emit('component-syntax',
                         'component comment name %r is not CGML_COMPONENT, '
                         'one space and a formal identifier' % name,
                         elem=node.elem)
            elif ident in seen:
                ctx.emit('component-syntax',
                         'component %r is defined twice in the state machine '
                         '%r (nodes %r and %r)' %
                         (ident, machine.id, seen[ident], node.id),
                         elem=node.elem)
            else:
                seen[ident] = node.id
            params, errors = meta.parse(node.body)
            for line, message in errors:
                ctx.emit('component-syntax',
                         '%s (value line %d)' % (message, line + 1),
                         elem=node.elem)
            types = [p.value.strip() for p in params if p.name == 'type']
            if not types or not types[0]:
                ctx.emit('component-syntax',
                         'component %r has no non-empty type parameter' %
                         ident,
                         elem=node.elem)


@rule('behaviour-syntax', 'CGML-6.8-1', 3, ERROR,
      'dData behaviour text follows the trigger syntax')
def _behaviour_syntax(ctx):
    """Report the parser errors under the rule each one names."""
    for node in model_mod.iter_nodes(ctx.model):
        for line, message, name in getattr(node, 'block_errors', ()):
            ctx.emit(name, '%s (value line %d)' % (message, line + 1),
                     elem=node.elem)
    for machine in ctx.model.machines:
        for transition in machine.transitions:
            for line, message, name in transition.block_errors:
                ctx.emit(name, '%s (value line %d)' % (message, line + 1),
                         elem=transition.elem)


@rule('meta-syntax', 'CGML-6.9-2', 3, ERROR,
      'metadata parameters follow the name/ value syntax')
def _meta_syntax(ctx):
    doc = ctx.model
    if doc.meta_comment is None:
        return
    for line, message in doc.meta_errors:
        ctx.emit('meta-syntax', '%s (value line %d)' % (message, line + 1),
                 elem=doc.meta_comment.elem)


@rule('meta-params', 'CGML-6.9-2', 3, ERROR,
      'metadata parameter names are latin letters, not repeated')
def _meta_params(ctx):
    doc = ctx.model
    seen = set()
    for par in doc.meta_params:
        if not LATIN_NAME_RE.match(par.name):
            ctx.emit('meta-params',
                     'parameter name %r is not latin letters only' % par.name,
                     elem=doc.meta_comment.elem)
        if par.name in seen:
            ctx.emit('meta-params',
                     'parameter %r is repeated; the first occurrence wins' %
                     par.name, elem=doc.meta_comment.elem)
        seen.add(par.name)


@rule('standard-version', 'CGML-6.9-3', 3, ERROR,
      'the standardVersion metadata parameter is "1.0"')
def _standard_version(ctx):
    doc = ctx.model
    if doc.meta_comment is None:
        return
    value = doc.param('standardVersion')
    if value is None:
        ctx.emit('standard-version',
                 'the mandatory standardVersion parameter is missing',
                 elem=doc.meta_comment.elem)
    elif value.strip() != '1.0':
        ctx.emit('standard-version',
                 'standardVersion is %r, expected "1.0"' % value,
                 elem=doc.meta_comment.elem)


@rule('geometry-mode-value', 'CGML-6.9-4-1', 3, ERROR,
      'the geometry metadata parameter is none, short or full')
def _geometry_mode_value(ctx):
    doc = ctx.model
    value = doc.param('geometry')
    if value is not None and value.strip() not in GEOMETRY_MODES:
        ctx.emit('geometry-mode-value',
                 'geometry mode %r is not admissible' % value,
                 elem=doc.meta_comment.elem)


@rule('transition-order-value', 'CGML-6.9-4-4', 3, WARNING,
      'the transitionOrder parameter is actionFirst or exitFirst')
def _transition_order_value(ctx):
    doc = ctx.model
    value = doc.param('transitionOrder')
    if value is not None and value.strip() not in TRANSITION_ORDERS:
        ctx.emit('transition-order-value',
                 'transitionOrder %r is not admissible' % value,
                 elem=doc.meta_comment.elem)


@rule('event-propagation-value', 'CGML-6.9-4-5', 3, ERROR,
      'the eventPropagation parameter is block or propagate')
def _event_propagation_value(ctx):
    doc = ctx.model
    value = doc.param('eventPropagation')
    if value is not None and value.strip() not in EVENT_PROPAGATIONS:
        ctx.emit('event-propagation-value',
                 'eventPropagation %r is not admissible (defer is valid '
                 'only per event)' % value, elem=doc.meta_comment.elem)


@rule('created-at', 'CGML-6.9-4-3', 3, INFO,
      'the createdAt parameter is an ISO 8601 UTC timestamp')
def _created_at(ctx):
    doc = ctx.model
    value = doc.param('createdAt')
    if value is None:
        return
    try:
        datetime.datetime.fromisoformat(value.strip())
    except ValueError:
        ctx.emit('created-at',
                 'createdAt %r is not an ISO 8601 timestamp' % value,
                 elem=doc.meta_comment.elem)


@rule('point-name-required', 'CGML-8.3-4', 3, ERROR,
      'entry and exit points carry a non-empty name')
def _point_name_required(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        if isinstance(node, model_mod.Vertex) and \
                node.kind in ('entryPoint', 'exitPoint') and \
                not (node.name or '').strip():
            ctx.emit('point-name-required',
                     '%s %r carries no non-empty dName' % (node.kind, node.id),
                     elem=node.elem)
