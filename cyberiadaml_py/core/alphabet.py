# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The EXT-FA alphabet comments: symbol lists and restricted regular expressions
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
"""The EXT-FA alphabet comments: symbol lists and restricted patterns."""
import re
from typing import List, Pattern, Tuple

from .actions import RESERVED

FA_INPUT = 'FA_INPUT'
FA_INPUT_RE = 'FA_INPUT_RE'
FA_OUTPUT = 'FA_OUTPUT'
FA_OUTPUT_RE = 'FA_OUTPUT_RE'
INPUT_NAMES = (FA_INPUT, FA_INPUT_RE)
OUTPUT_NAMES = (FA_OUTPUT, FA_OUTPUT_RE)
NAMES = INPUT_NAMES + OUTPUT_NAMES
RE_SUFFIX = '_RE'

EOF = 'EOF'
RESERVED_SYMBOLS = RESERVED + ('ANY', 'UNKNOWN', EOF)   # FA 3.4

ESCAPABLE = '.[]-{},?()|\\'      # the characters an alphabet escapes (FA 4)
FORBIDDEN = '*+^$'               # the constructs of an infinite set
ANY_CHAR = r'[^\s]'              # '.' - one printable non-space character
COUNT_RE = re.compile(r'\{(\d+)(?:,(\d+))?\}')


class AlphabetError(ValueError):
    """A restricted regular expression outside the FA 4 grammar."""

    def __init__(self, message: str, position: int):
        super().__init__(message)
        self.position = position


class Alphabet:
    """The symbols (or the patterns) of one FA_* comment."""

    def __init__(self, name: str):
        self.name = name
        self.regex = name.endswith(RE_SUFFIX)
        self.symbols: List[str] = []
        self.patterns: List[Pattern[str]] = []
        self.errors: List[Tuple[int, str]] = []     # (line index, message)

    def contains(self, symbol: str) -> bool:
        """Return whether the symbol is a member of the alphabet."""
        if symbol in RESERVED_SYMBOLS:
            return False
        if self.regex:
            return any(p.fullmatch(symbol) for p in self.patterns)
        return symbol in self.symbols


def parse(name: str, body) -> Alphabet:
    """Parse an alphabet comment body: one symbol or pattern per line."""
    alphabet = Alphabet(name)
    lines = (body or '').split('\n')
    filled = [i for i, line in enumerate(lines) if line.strip()]
    if not filled:
        alphabet.errors.append((0, 'the alphabet is empty'))
        return alphabet
    for i in range(filled[0], filled[-1] + 1):
        line = lines[i].strip()
        if not line:
            alphabet.errors.append((i, 'empty line in the alphabet'))
        elif alphabet.regex:
            try:
                alphabet.patterns.append(re.compile(translate(line)))
            except AlphabetError as err:
                alphabet.errors.append(
                    (i, '%s (column %d)' % (err, err.position + 1)))
        else:
            alphabet.symbols.append(line)
    return alphabet


def translate(expr: str) -> str:
    """Return the Python pattern of a restricted regular expression (FA 4)."""
    if not expr:
        raise AlphabetError('empty expression', 0)
    source, pos = _sequence(expr, 0, top=True)
    return source


def _sequence(expr, pos, top):
    parts = []
    quantifiable = False
    while pos < len(expr):
        ch = expr[pos]
        if ch in ')|':
            if top:
                raise AlphabetError('%r outside a group' % ch, pos)
            break
        if ch in FORBIDDEN:
            raise AlphabetError('construct %r is not admissible' % ch, pos)
        if ch == '?':
            if not quantifiable:
                raise AlphabetError("'?' follows nothing", pos)
            parts.append(ch)
            quantifiable = False
            pos += 1
        elif ch == '{':
            if not quantifiable:
                raise AlphabetError('count follows nothing', pos)
            match = COUNT_RE.match(expr, pos)
            if match is None:
                raise AlphabetError('count {n} or {n,m} expected', pos)
            low, high = match.group(1), match.group(2)
            if high is not None and int(high) < int(low):
                raise AlphabetError('count {n,m} with m < n', pos)
            parts.append(match.group(0))
            quantifiable = False
            pos = match.end()
        elif ch in ']}-,':
            raise AlphabetError('%r must be escaped' % ch, pos)
        elif ch == '\\':
            parts.append(re.escape(_escaped(expr, pos)))
            quantifiable = True
            pos += 2
        elif ch == '.':
            parts.append(ANY_CHAR)
            quantifiable = True
            pos += 1
        elif ch == '[':
            source, pos = _char_class(expr, pos + 1)
            parts.append(source)
            quantifiable = True
        elif ch == '(':
            source, pos = _group(expr, pos + 1)
            parts.append(source)
            quantifiable = True
        else:
            parts.append(re.escape(ch))
            quantifiable = True
            pos += 1
    return ''.join(parts), pos


def _escaped(expr, pos):
    """Return the character the escape at pos denotes."""
    if pos + 1 >= len(expr) or expr[pos + 1] not in ESCAPABLE:
        raise AlphabetError('unknown escape', pos)
    return expr[pos + 1]


def _group(expr, pos):
    start = pos - 1
    branches = []
    while True:
        source, pos = _sequence(expr, pos, top=False)
        if not source:
            raise AlphabetError('empty alternative', pos)
        branches.append(source)
        if pos >= len(expr):
            raise AlphabetError("unbalanced '('", start)
        pos += 1
        if expr[pos - 1] == ')':
            return '(?:%s)' % '|'.join(branches), pos


def _class_item(expr, pos):
    """Return one character of a class and the position after it."""
    ch = expr[pos]
    if ch == '\\':
        return _escaped(expr, pos), pos + 2
    if ch in '[^-':
        raise AlphabetError('%r must be escaped' % ch, pos)
    return ch, pos + 1


def _char_class(expr, pos):
    start = pos - 1
    items = []
    while pos < len(expr) and expr[pos] != ']':
        low, pos = _class_item(expr, pos)
        if pos + 1 < len(expr) and expr[pos] == '-' and expr[pos + 1] != ']':
            high, pos = _class_item(expr, pos + 1)
            if high < low:
                raise AlphabetError('range out of order', pos - 1)
            items.append(re.escape(low) + '-' + re.escape(high))
        else:
            items.append(re.escape(low))
    if pos >= len(expr):
        raise AlphabetError("unbalanced '['", start)
    if not items:
        raise AlphabetError('empty character class', start)
    return '[%s]' % ''.join(items), pos + 1
