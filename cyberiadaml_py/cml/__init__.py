# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The CyberiadaML interface in pure Python
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
"""The interface of the CyberiadaML binding over the core (see CML.md).

A program written for the binding imports the module in its place::

  try:
      import CyberiadaML
  except ImportError:
      from cyberiadaml_py import cml as CyberiadaML
"""
from .actions import Action
from .document import Document, DocumentMetainformation, LocalDocument
from .elements import (Choice, Comment, CommentSubject, ConnectionPoint,
                       Element, ElementCollection, Final, History, Initial,
                       Pseudostate, State, StateMachine, SubmachineState,
                       Terminate, Transition, Vertex)
from .enums import *
from .errors import (ActionException, AssertException, CybMLException,
                     Exception, FileException, FormatException,
                     MetainfoException, NotFoundException,
                     NotImplementedException, ParametersException,
                     XMLException)
from .enums import (DocumentFormat, formatLegacyYED,
                    formatLegacyYEDBerloga16, formatLegacyYEDOstranna)
from .geometry import Point, Polyline, Rect

__version__ = '1.7.0'


def is_legacy_yed_format(f: DocumentFormat) -> bool:
    """Return True for the yEd formats."""
    return f in (formatLegacyYED, formatLegacyYEDOstranna,
                 formatLegacyYEDBerloga16)


def cleanup_library() -> None:
    """Do nothing: there is no C library to clean up."""
