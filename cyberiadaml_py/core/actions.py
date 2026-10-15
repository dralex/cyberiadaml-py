# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The parser of the 6.8 behaviour text (triggers, guards, behaviour blocks)
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
"""The parser of the 6.8 behaviour text: triggers, guards, blocks."""
from dataclasses import dataclass, field
from typing import Optional

ENTRY = 'entry'
EXIT = 'exit'
DO = 'do'
EVENT = 'event'

KEYWORDS = (ENTRY, EXIT, DO)
EVENT_PARAMS = ('propagate', 'block', 'defer')
PRE_PARAMS = ('propagate', 'block')   # directly before the '/' separator
DEFER = 'defer'                       # directly after the '/' separator
RESERVED = KEYWORDS + EVENT_PARAMS + ('else',)   # not event names (6.8.1)
SYNTAX = 'behaviour-syntax'
RESERVED_RULE = 'event-name-reserved'
DEFER_RULE = 'defer-usage'
PARAM_RULE = 'param-needs-event'
ONCE_RULE = 'behaviour-block-once'


@dataclass
class Block:
    """One block of a behaviour text."""

    kind: str                      # entry | exit | do | event
    trigger: str = ''              # event name, verbatim (event blocks)
    param: Optional[str] = None    # propagate | block | defer
    guard: Optional[str] = None    # guard text, bracket escapes resolved
    behaviour: list = field(default_factory=list)
    verbatim: str = ''


def _escaped(line, idx):
    return idx > 0 and line[idx - 1] == '\\'


def _find_separator(text):
    """Return the header separator.

    It is the first '/' followed by a space, a newline or the text end.
    """
    idx = 0
    while True:
        idx = text.find('/', idx)
        if idx < 0:
            return -1
        if idx == len(text) - 1 or text[idx + 1] in ' \n':
            return idx
        idx += 1


def _find_guard(text, end):
    """Return the last unescaped [...] pair directly before end."""
    close = end - 1
    while close >= 0 and text[close] in ' \n\t\r':
        close -= 1
    if close < 0 or text[close] != ']' or _escaped(text, close):
        return None
    start = close - 1
    while start >= 0:
        if text[start] == '[' and not _escaped(text, start):
            return start, close
        start -= 1
    return None


def _strip_param(head):
    """Split a trailing propagate/block keyword off the header text."""
    words = head.split()
    if words and words[-1] in PRE_PARAMS:
        return head[:head.rfind(words[-1])].rstrip(), words[-1]
    return head, None


def _resolve_brackets(text):
    return text.replace('\\[', '[').replace('\\]', ']')


def _parse_header(text, lineno, errors, transition):
    """Parse a block header; return (block, inline behaviour or None).

    In both contexts the separator may be omitted when no behaviour
    follows; a transition header may additionally span several lines up
    to the separator.
    """
    stripped = text.rstrip()
    for keyword in KEYWORDS:
        prefix = keyword + '/'
        if stripped.startswith(prefix):
            inline = stripped[len(prefix):]
            if inline.startswith(' '):
                inline = inline[1:]
            if transition:
                errors.append((lineno, 'the %s block belongs to a state, '
                               'not to a transition' % prefix, RESERVED_RULE))
            return Block(keyword), inline or None
    sep = _find_separator(stripped)
    if sep < 0:
        head, inline = stripped, None
    else:
        head = stripped[:sep].rstrip()
        inline = stripped[sep + 1:]
        if inline.startswith(' '):
            inline = inline[1:]
    # propagate/block sit directly before the separator, after the guard
    head, param = _strip_param(head)
    guard = None
    span = _find_guard(head, len(head))
    if span is not None:
        start, close = span
        guard = _resolve_brackets(head[start + 1:close])
        head = head[:start].rstrip()
    # defer sits directly after the separator
    if inline is not None and param is None and \
            (inline == DEFER or inline.startswith(DEFER + ' ')):
        param = DEFER
        inline = inline[len(DEFER):].lstrip()
        if transition:
            errors.append((lineno, 'defer on a transition; it belongs to an '
                           'internal transition of a state', DEFER_RULE))
        if inline:
            errors.append((lineno, 'behaviour %r after defer' % inline,
                           DEFER_RULE))
    trigger = head
    if trigger.strip() in RESERVED:
        errors.append((lineno, 'event name %r is a reserved word' %
                       trigger.strip(), RESERVED_RULE))
    if param in PRE_PARAMS and not trigger.strip():
        errors.append((lineno, '%s without an event name' % param,
                       PARAM_RULE))
    # an event description without the event name is a completion transition
    return Block(EVENT, trigger=trigger, param=param, guard=guard), \
        inline or None


def parse(text, transition=False):
    """Parse a dData behaviour value; return (blocks, errors).

    Blocks are separated by blank lines; an empty value is zero blocks.
    Errors are (line index, message, rule) triples for the L3 checks:
    the syntax rule, or one of the 6.8.1/6.8.2 constraints (reserved event
    names, defer placement, propagate/block without an event, repeated
    entry/exit/do blocks). The transition flag selects the label grammar
    of edges (separator optional) over the node grammar (separator
    mandatory).
    """
    blocks = []
    errors = []
    if text is None:
        return blocks, errors
    lines = text.split('\n')
    run = []      # (line index, line) of the current block
    for lineno, line in enumerate(lines + ['']):
        if line.strip():
            run.append((lineno, line))
            continue
        if not run:
            continue
        # a transition header runs up to the first line carrying the
        # separator (without one the whole block is the event); a node
        # block header is its first line, and behaviour lines demand the
        # separator on it
        header_end = 0
        if transition:
            header_end = len(run) - 1
            for offset, (_, text_line) in enumerate(run):
                if _find_separator(text_line.rstrip()) >= 0:
                    header_end = offset
                    break
        elif len(run) > 1 and _find_separator(run[0][1].rstrip()) < 0:
            errors.append((run[0][0],
                           "missing '/' before the behaviour lines", SYNTAX))
        header = '\n'.join(text_line for _, text_line in run[:header_end + 1])
        block, inline = _parse_header(header, run[0][0], errors, transition)
        if inline:
            block.behaviour.append(inline)
        block.behaviour.extend(text_line for _, text_line in
                               run[header_end + 1:])
        block.verbatim = '\n'.join(text for _, text in run)
        if block.param == DEFER and block.behaviour:
            errors.append((run[0][0], 'behaviour lines after defer',
                           DEFER_RULE))
        if block.kind in KEYWORDS and \
                any(b.kind == block.kind for b in blocks):
            errors.append((run[0][0], 'a second %s/ block' % block.kind,
                           ONCE_RULE))
        blocks.append(block)
        run = []
    return blocks, errors
