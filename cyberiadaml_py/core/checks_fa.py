# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The EXT-FA rules: deterministic finite automaton documents (type/ fa)
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
"""The EXT-FA rules: deterministic finite automaton documents (type/ fa)."""
from . import alphabet
from .actions import ENTRY, EVENT
from .findings import ERROR
from .model import Comment, State, SubmachineState, Vertex
from .rules import declare, rule

INITIAL = 'initial'
FINAL = 'final'
FA_VERTICES = (INITIAL, FINAL)
EOF = alphabet.EOF
BLOCK = 'block'
FORMAL = 'formal'

# Every rule below applies to an FA document only: the model recognises the
# metadata parameter type/ fa (Document.is_fa), the rules return at once
# otherwise.
declare('fa-type', 'CGML-FA-5-1', 3, ERROR,
        'type/ fa in the metadata selects the EXT-FA rules',
        note='recognised by the model (Document.is_fa), never reported')


def _fa(ctx):
    return ctx.model is not None and ctx.model.is_fa


def _nodes(machine):
    """Yield the (node, parent state) pairs, region children included."""
    def walk(children, parent):
        for child in children:
            yield child, parent
            for region in getattr(child, 'regions', ()):
                yield from walk(region.children, child)
    yield from walk(machine.children, None)


def _index(machine):
    return {node.id: node for node, _ in _nodes(machine)}


def _kind(node):
    return (node.kind or '').strip() if isinstance(node, Vertex) else None


def _events(transition):
    return [b for b in transition.blocks if b.kind == EVENT]


def _event(transition):
    """Return the event name of a single-event transition, None otherwise."""
    blocks = _events(transition)
    return blocks[0].trigger.strip() if len(blocks) == 1 else None


def _state_transitions(machine, index):
    """Yield the transitions of the automaton: those leaving a state."""
    for transition in machine.transitions:
        if isinstance(index.get(transition.source), State):
            yield transition


def _alphabet_comments(machine):
    for node, parent in _nodes(machine):
        if isinstance(node, Comment) and node.name in alphabet.NAMES:
            yield node, parent


def _alphabets(machine):
    """Return the parsed input and output alphabets, None when not declared."""
    found = {}
    for node, _ in _alphabet_comments(machine):
        kind = alphabet.INPUT_NAMES if node.name in alphabet.INPUT_NAMES \
            else alphabet.OUTPUT_NAMES
        found.setdefault(kind, alphabet.parse(node.name, node.body))
    return found.get(alphabet.INPUT_NAMES), found.get(alphabet.OUTPUT_NAMES)


def _symbol_lines(block):
    return [line.strip() for line in block.behaviour]


# L3 ----------------------------------------------------------------------

@rule('fa-event-propagation', 'CGML-FA-5-3', 3, ERROR,
      'an FA document propagates no events: eventPropagation absent or block')
def _fa_event_propagation(ctx):
    if not _fa(ctx):
        return
    value = ctx.model.param('eventPropagation')
    if value is not None and value.strip() != BLOCK:
        ctx.emit('fa-event-propagation',
                 'eventPropagation %r in an FA document, block expected' %
                 value.strip(), elem=ctx.model.meta_comment.elem)


@rule('fa-state-behaviour', 'CGML-FA-3.1-1', 3, ERROR,
      'an FA state holds at most a one-line entry/ block, the output symbol')
def _fa_state_behaviour(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        for node, _ in _nodes(machine):
            if not isinstance(node, State):
                continue
            for block in node.blocks:
                if block.kind != ENTRY:
                    ctx.emit('fa-state-behaviour',
                             'state %r has a %s block; only entry/ is '
                             'admissible in an FA diagram' %
                             (node.id, block.kind), elem=node.elem)
                elif len(_symbol_lines(block)) != 1:
                    ctx.emit('fa-state-behaviour',
                             'the entry/ block of state %r has %d lines, '
                             'one output symbol expected' %
                             (node.id, len(block.behaviour)), elem=node.elem)


@rule('fa-initial-transition', 'CGML-FA-3.2-2', 3, ERROR,
      'the transition from an initial pseudostate has no event, guard, action')
def _fa_initial_transition(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        index = _index(machine)
        for transition in machine.transitions:
            if _kind(index.get(transition.source)) == INITIAL \
                    and transition.blocks:
                ctx.emit('fa-initial-transition',
                         'transition %r from the initial pseudostate carries '
                         'a label' % transition.id, elem=transition.elem)


@rule('fa-transition-label', 'CGML-FA-3.4-1', 3, ERROR,
      'an FA transition carries one symbol: no guard, no event parameters')
def _fa_transition_label(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        index = _index(machine)
        for transition in _state_transitions(machine, index):
            events = _events(transition)
            if len(events) != 1:
                ctx.emit('fa-transition-label',
                         'transition %r carries %d events, exactly one '
                         'symbol expected' % (transition.id, len(events)),
                         elem=transition.elem)
                continue
            block = events[0]
            trigger = block.trigger.strip()
            if not trigger or '\n' in trigger:
                ctx.emit('fa-transition-label',
                         'transition %r has no single-line symbol' %
                         transition.id, elem=transition.elem)
            if block.guard is not None:
                ctx.emit('fa-transition-label',
                         'transition %r carries a guard' % transition.id,
                         elem=transition.elem)
            if block.param is not None:
                ctx.emit('fa-transition-label',
                         'transition %r carries the parameter %r' %
                         (transition.id, block.param), elem=transition.elem)


@rule('fa-transition-action', 'CGML-FA-3.4-2', 3, ERROR,
      'an FA transition action is at most one line, the output symbol')
def _fa_transition_action(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        index = _index(machine)
        for transition in _state_transitions(machine, index):
            for block in _events(transition):
                if len(block.behaviour) > 1:
                    ctx.emit('fa-transition-action',
                             'transition %r has %d action lines, one output '
                             'symbol expected' %
                             (transition.id, len(block.behaviour)),
                             elem=transition.elem)


@rule('fa-symbol-reserved', 'CGML-FA-3.4-3', 3, ERROR,
      'an FA symbol is no reserved word and no reserved event name')
def _fa_symbol_reserved(ctx):
    if not _fa(ctx):
        return

    def check(symbol, where, elem):
        if symbol in alphabet.RESERVED_SYMBOLS:
            ctx.emit('fa-symbol-reserved',
                     'reserved name %r used as %s' % (symbol, where),
                     elem=elem)

    for machine in ctx.model.machines:
        index = _index(machine)
        for node, _ in _nodes(machine):
            if isinstance(node, State):
                for block in node.blocks:
                    for line in _symbol_lines(block):
                        check(line, 'the output symbol of state %r' %
                              node.id, node.elem)
            elif isinstance(node, Comment) and node.name in alphabet.NAMES \
                    and not node.name.endswith(alphabet.RE_SUFFIX):
                for line in alphabet.parse(node.name, node.body).symbols:
                    check(line, 'a symbol of %s' % node.name, node.elem)
        for transition in _state_transitions(machine, index):
            for block in _events(transition):
                trigger = block.trigger.strip()
                if trigger != EOF:
                    check(trigger, 'the symbol of transition %r' %
                          transition.id, transition.elem)
                for line in _symbol_lines(block):
                    check(line, 'the output symbol of transition %r' %
                          transition.id, transition.elem)


@rule('fa-alphabet-syntax', 'CGML-FA-4-2', 3, ERROR,
      'an alphabet comment lists one symbol or restricted pattern per line')
def _fa_alphabet_syntax(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        for node, _ in _alphabet_comments(machine):
            for line, message in alphabet.parse(node.name, node.body).errors:
                ctx.emit('fa-alphabet-syntax',
                         '%s: %s (value line %d)' % (node.name, message,
                                                     line + 1),
                         elem=node.elem)


# L4 ----------------------------------------------------------------------

@rule('fa-single-machine', 'CGML-FA-5-2', 4, ERROR,
      'an FA document contains one state machine')
def _fa_single_machine(ctx):
    if not _fa(ctx):
        return
    machines = ctx.model.machines
    if len(machines) != 1:
        ctx.emit('fa-single-machine',
                 'FA document with %d state machines' % len(machines),
                 elem=machines[-1].elem)


@rule('fa-element-set', 'CGML-FA-3-1', 4, ERROR,
      'an FA diagram uses states, initial, final, transitions, comments only')
def _fa_element_set(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        for node, _ in _nodes(machine):
            if isinstance(node, Vertex) and _kind(node) not in FA_VERTICES:
                ctx.emit('fa-element-set', 'vertex %r of kind %r' %
                         (node.id, _kind(node)), elem=node.elem)
            elif isinstance(node, SubmachineState):
                ctx.emit('fa-element-set', 'submachine state %r' % node.id,
                         elem=node.elem)
            elif isinstance(node, State) and node.collapsed:
                ctx.emit('fa-element-set',
                         'collapsed decomposition block on state %r' %
                         node.id, elem=node.elem)


@rule('fa-composite', 'CGML-FA-3.1.1-1', 4, ERROR,
      'an FA composite state has one region and no entry/ block')
def _fa_composite(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        for node, _ in _nodes(machine):
            if not isinstance(node, State) or not node.regions:
                continue
            if len(node.regions) != 1:
                ctx.emit('fa-composite', 'composite state %r has %d regions' %
                         (node.id, len(node.regions)), elem=node.elem)
            if any(b.kind == ENTRY for b in node.blocks):
                ctx.emit('fa-composite',
                         'composite state %r has an entry/ block' % node.id,
                         elem=node.elem)


@rule('fa-composite-initial', 'CGML-FA-3.1.1-2', 4, ERROR,
      'a composite state entered by a transition contains an initial')
def _fa_composite_initial(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        index = _index(machine)
        entered = set()
        for transition in machine.transitions:
            target = index.get(transition.target)
            if isinstance(target, State) and target.regions \
                    and target.id not in entered:
                entered.add(target.id)
                if not any(_kind(n) == INITIAL for region in target.regions
                           for n in region.children):
                    ctx.emit('fa-composite-initial',
                             'composite state %r is entered by transition %r '
                             'but contains no initial pseudostate' %
                             (target.id, transition.id), elem=target.elem)


@rule('fa-deterministic', 'CGML-FA-3.1.1-3', 4, ERROR,
      'a state has at most one own transition per symbol')
def _fa_deterministic(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        index = _index(machine)
        seen = {}
        for transition in _state_transitions(machine, index):
            event = _event(transition)
            if event is None:
                continue
            first = seen.setdefault((transition.source, event), transition)
            if first is not transition:
                ctx.emit('fa-deterministic',
                         'transitions %r and %r leave state %r by the same '
                         'symbol %r' % (first.id, transition.id,
                                        transition.source, event),
                         elem=transition.elem)


@rule('fa-top-initial', 'CGML-FA-3.2-1', 4, ERROR,
      'the top level of an FA state machine holds one initial pseudostate',
      also=('CGML-6.4-4-1', 'CGML-6.4-4-2'))
def _fa_top_initial(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        count = sum(1 for n in machine.children if _kind(n) == INITIAL)
        if count != 1:
            ctx.emit('fa-top-initial',
                     'state machine %r has %d top-level initial pseudostates' %
                     (machine.id, count), elem=machine.elem)


@rule('fa-final-top-level', 'CGML-FA-3.3-1', 4, ERROR,
      'FA final states sit at the top level of the state machine')
def _fa_final_top_level(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        for node, parent in _nodes(machine):
            if _kind(node) == FINAL and parent is not None:
                ctx.emit('fa-final-top-level',
                         'final state %r inside composite state %r' %
                         (node.id, parent.id), elem=node.elem)


@rule('fa-eof-final', 'CGML-FA-3.3-2', 4, ERROR,
      'a transition into a final state carries EOF and EOF leads to a final')
def _fa_eof_final(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        index = _index(machine)
        for transition in machine.transitions:
            if _kind(index.get(transition.source)) == INITIAL:
                is_eof = False
            else:
                is_eof = _event(transition) == EOF
            to_final = _kind(index.get(transition.target)) == FINAL
            if is_eof and not to_final:
                ctx.emit('fa-eof-final',
                         'EOF transition %r targets %r, not a final state' %
                         (transition.id, transition.target),
                         elem=transition.elem)
            elif to_final and not is_eof:
                ctx.emit('fa-eof-final',
                         'transition %r into the final state %r carries no '
                         'EOF' % (transition.id, transition.target),
                         elem=transition.elem)


@rule('fa-alphabet-comments', 'CGML-FA-4-1', 4, ERROR,
      'one input and one output alphabet comment, formal, at the top level')
def _fa_alphabet_comments(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        seen = {}
        for node, parent in _alphabet_comments(machine):
            if (node.kind or '').strip() != FORMAL:
                ctx.emit('fa-alphabet-comments',
                         'alphabet comment %r (%s) is not formal' %
                         (node.id, node.name), elem=node.elem)
            if parent is not None:
                ctx.emit('fa-alphabet-comments',
                         'alphabet comment %r (%s) inside state %r, the top '
                         'level expected' % (node.id, node.name, parent.id),
                         elem=node.elem)
            kind = 'input' if node.name in alphabet.INPUT_NAMES else 'output'
            first = seen.setdefault(kind, node)
            if first is not node:
                ctx.emit('fa-alphabet-comments',
                         'second %s alphabet comment %r (%s) after %r (%s)' %
                         (kind, node.id, node.name, first.id, first.name),
                         elem=node.elem)


@rule('fa-alphabet-membership', 'CGML-FA-4-3', 4, ERROR,
      'the symbols of the diagram belong to the declared alphabets')
def _fa_alphabet_membership(ctx):
    if not _fa(ctx):
        return
    for machine in ctx.model.machines:
        index = _index(machine)
        inputs, outputs = _alphabets(machine)
        if inputs is not None and inputs.errors:
            inputs = None
        if outputs is not None and outputs.errors:
            outputs = None
        if inputs is None and outputs is None:
            continue

        def check(table, symbol, where, elem):
            if table is not None and not table.contains(symbol):
                ctx.emit('fa-alphabet-membership',
                         '%s %r is not in %s' % (where, symbol, table.name),
                         elem=elem)

        for node, _ in _nodes(machine):
            if isinstance(node, State):
                for block in node.blocks:
                    for line in _symbol_lines(block):
                        check(outputs, line, 'the output symbol of state %r' %
                              node.id, node.elem)
        for transition in _state_transitions(machine, index):
            for block in _events(transition):
                trigger = block.trigger.strip()
                if trigger != EOF:
                    check(inputs, trigger, 'the symbol of transition %r' %
                          transition.id, transition.elem)
                for line in _symbol_lines(block):
                    check(outputs, line, 'the output symbol of transition %r'
                          % transition.id, transition.elem)
