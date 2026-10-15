# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The parser of the 6.9 metadata parameter text (name/ value lists)
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
"""The parser of the 6.9 metadata parameter text (name/ value lists)."""
from dataclasses import dataclass


@dataclass
class Param:
    """A metadata parameter."""

    name: str
    value: str
    line: int      # line index of the parameter inside the text


def parse(text):
    """Parse a metadata parameter list; return (params, errors).

    Parameters are separated by blank lines; the first line of a chunk is
    'name/ value' (spaces and tabs around the '/' are trimmed), the
    following chunk lines continue the value. The same grammar parses the
    CGML_COMPONENT bodies. Errors are (line index, message) pairs.
    """
    params = []
    errors = []
    if text is None:
        return params, errors
    lines = text.split('\n')
    run = []
    for lineno, line in enumerate(lines + ['']):
        if line.strip():
            run.append((lineno, line))
            continue
        if not run:
            continue
        header_lineno, header = run[0]
        sep = header.find('/')
        if sep < 0:
            errors.append((header_lineno,
                           "missing '/' in the parameter description"))
        else:
            name = header[:sep].strip(' \t')
            value = header[sep + 1:].lstrip(' \t')
            for _, extra in run[1:]:
                value += '\n' + extra
            if not name:
                errors.append((header_lineno, 'empty parameter name'))
            else:
                params.append(Param(name, value, header_lineno))
        run = []
    return params, errors
