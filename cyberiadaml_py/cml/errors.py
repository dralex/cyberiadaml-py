# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The exceptions of the CyberiadaML interface
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
"""The exceptions of the CyberiadaML interface.

The hierarchy of the C++ library; the binding registers the classes flat,
so this one catches what the binding catches and more.
"""
import builtins


class Exception(builtins.Exception):
    """The base of the exceptions of the interface."""

    kind = 'Generic Error'


class FileException(Exception):
    """A file cannot be read or written."""

    kind = 'File Exception'


class FormatException(Exception):
    """The document breaks its format."""

    kind = 'Format Exception'


class XMLException(FormatException):
    """The document is not well-formed XML."""

    kind = 'XML Exception'


class CybMLException(FormatException):
    """The document breaks the CyberiadaML-GraphML format."""

    kind = 'CyberiadaML Exception'


class ActionException(CybMLException):
    """A behaviour text breaks its grammar."""

    kind = 'Action Exception'


class MetainfoException(FormatException):
    """The metainformation of the document is wrong."""

    kind = 'Metainfo Exception'


class ParametersException(Exception):
    """A call got a wrong parameter."""

    kind = 'Parameters Exception'


class NotFoundException(ParametersException):
    """An element is not found."""

    kind = 'Not Found Exception'


class AssertException(Exception):
    """An internal check failed."""

    kind = 'Assert Exception'


class NotImplementedException(Exception):
    """The feature is not provided by the pure-Python interface."""

    kind = 'Not Implemented Exception'


def error(cls, message: str) -> Exception:
    """Return an exception of cls with the message form of the library."""
    return cls('%s: %s' % (cls.kind, message))
