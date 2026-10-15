# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The validation findings and reports
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
"""The validation findings and reports."""
from dataclasses import dataclass
from typing import Optional

ERROR = 'ERROR'
WARNING = 'WARNING'
INFO = 'INFO'

LAST_LAYER = 4


@dataclass
class Finding:
    """A finding of a rule, with its requirement and position."""

    rule: str
    req: Optional[str]
    layer: int
    severity: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    path: Optional[str] = None

    def render(self, filename):
        """Return the text line of the finding."""
        pos = ''
        if self.line is not None:
            pos = ':%d' % self.line
            if self.column is not None:
                pos += ':%d' % self.column
        req = ' ' + self.req if self.req else ''
        at = ' (at %s)' % self.path if self.path else ''
        return '%s%s: %s%s [L%d] %s%s' % (
            filename, pos, self.severity, req, self.layer, self.message, at)

    def to_json(self):
        """Return the finding as a JSON object."""
        return {
            'rule': self.rule,
            'req': self.req,
            'layer': self.layer,
            'severity': self.severity,
            'message': self.message,
            'line': self.line,
            'column': self.column,
            'path': self.path,
        }


class Report:
    """The findings of one document run through the validation layers."""

    def __init__(self):
        self.findings = []
        self.layers_run = []

    def add(self, finding):
        """Add a finding."""
        self.findings.append(finding)

    def has_errors(self, layer=None):
        """Return whether an ERROR was found, at a layer or at any."""
        return any(f.severity == ERROR and (layer is None or f.layer == layer)
                   for f in self.findings)

    def has_warnings(self):
        """Return whether a WARNING was found."""
        return any(f.severity == WARNING for f in self.findings)

    def valid(self, strict=False):
        """Return the verdict; strict fails on warnings too."""
        if self.has_errors():
            return False
        return not (strict and self.has_warnings())

    def verdict(self, strict=False):
        """Return the verdict word."""
        return 'valid' if self.valid(strict) else 'invalid'

    def render_text(self, filename):
        """Return the text lines of the report."""
        lines = [f.render(filename) for f in self.findings]
        stopped = self.layers_run[-1] if self.layers_run else 0
        if self.has_errors() and stopped < LAST_LAYER:
            lines.append('%s: layers L%d-L%d not evaluated' %
                         (filename, stopped + 1, LAST_LAYER))
        return lines

    def to_json(self, filename, strict=False):
        """Return the report as a JSON object."""
        return {
            'file': filename,
            'verdict': self.verdict(strict),
            'layers_run': self.layers_run,
            'findings': [f.to_json() for f in self.findings],
        }
