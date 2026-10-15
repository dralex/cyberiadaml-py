# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The standard-compliant core: reading, writing and the canonical dump
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
"""The standard-compliant core: reading, writing and the canonical dump."""
from .actions import Block
from .dialect import FORMAT_LAPKI
from .dialect import FORMAT_VALUE as FORMAT_STANDARD
from .dump import render as _render
from .findings import ERROR, INFO, WARNING, Finding
from .meta import Param
from .model import (Comment, CommentLink, Document, Extension, KeyDecl,
                    Node, Point, Rect, Region, State, StateMachine,
                    SubmachineState, Transition, Vertex)
from .reader import CGMLError, read

__all__ = [
    'read', 'dump', 'CGMLError', 'FORMAT_STANDARD', 'FORMAT_LAPKI',
    'ERROR', 'WARNING', 'INFO', 'Finding', 'Block', 'Param', 'Comment',
    'CommentLink', 'Document', 'Extension', 'KeyDecl', 'Node', 'Point',
    'Rect', 'Region', 'State', 'StateMachine', 'SubmachineState',
    'Transition', 'Vertex',
]


def dump(document: Document) -> str:
    """Return the canonical dump of a document."""
    return _render(document)
