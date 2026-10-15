# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The validation rule registry and the layer runner
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
"""The validation rule registry and the layer runner."""
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .findings import Finding, Report
from .requirements import DIALECT_REQUIREMENTS, REQUIREMENTS


@dataclass
class Rule:
    """A registered check: its requirement, layer and severity."""

    name: str
    req: Optional[str]
    layer: int
    severity: str
    title: str
    func: Optional[Callable] = None
    note: Optional[str] = None
    also: tuple = ()      # further requirement ids the rule covers


REGISTRY: Dict[str, Rule] = {}


def _register(rule_obj):
    if rule_obj.name in REGISTRY:
        raise ValueError('duplicate rule name: %s' % rule_obj.name)
    for req in (rule_obj.req,) + tuple(rule_obj.also):
        if req is not None and req not in REQUIREMENTS \
                and req not in DIALECT_REQUIREMENTS:
            raise ValueError('unknown requirement: %s' % req)
    REGISTRY[rule_obj.name] = rule_obj


def rule(name, req, layer, severity, title, also=()):
    """Register a callable check; the callable receives the layer context."""
    def decorator(func):
        _register(Rule(name, req, layer, severity, title, func, None,
                       tuple(also)))
        return func
    return decorator


def declare(name, req, layer, severity, title, note=None, also=()):
    """Register a rule emitted by a walker or the parser (no callable)."""
    _register(Rule(name, req, layer, severity, title, None, note,
                   tuple(also)))


def cited(registry=None):
    """All requirement ids the registered rules cover."""
    ids = set()
    for rule_obj in (registry or REGISTRY).values():
        if rule_obj.req is not None:
            ids.add(rule_obj.req)
        ids.update(rule_obj.also)
    return ids


class Context:
    """The state passed to the checks of one validation layer."""

    def __init__(self, report, filename):
        self.report = report
        self.filename = filename
        self.layer = 0
        self.parsed = None   # xmlload.ParsedDocument after L1
        self.model = None    # model.Document after the model build
        self.dialect = None  # dialect.Result when a dialect pass ran

    def emit(self, name, message, elem=None, line=None, column=None,
             path=None):
        """Report a finding of the named rule, located at elem."""
        rule_obj = REGISTRY[name]
        if elem is not None and self.parsed is not None:
            info = self.parsed.info.get(elem)
            if info is not None:
                line = info[0] if line is None else line
                column = info[1] if column is None else column
                path = info[2] if path is None else path
        self.report.add(Finding(name, rule_obj.req, rule_obj.layer,
                                rule_obj.severity, message, line, column,
                                path))


def load_checks():
    """Import the check modules so that their rules register."""
    from . import (checks_l3, checks_l4, dialect,  # noqa: F401
                   tagtree, xmlload)


def run_layer(ctx, layer):
    """Run the callable checks of one layer."""
    ctx.layer = layer
    for rule_obj in REGISTRY.values():
        if rule_obj.layer == layer and rule_obj.func is not None:
            rule_obj.func(ctx)
    ctx.report.layers_run.append(layer)


def run_document(data, filename='<data>', dialect=None):
    """Run the validation layers over the document bytes; return the context.

    A dialect name runs its repair pass between L1 and L2 (layer 0).
    """
    from . import dialect as dialect_pass
    from . import model, tagtree, xmlload

    load_checks()
    ctx = Context(Report(), filename)
    ctx.layer = 1
    ctx.parsed = xmlload.load(data, ctx)
    ctx.report.layers_run.append(1)
    if ctx.report.has_errors(layer=1) or ctx.parsed is None:
        return ctx
    if dialect is not None:
        ctx.layer = 0
        ctx.dialect = dialect_pass.apply(ctx, dialect)
    ctx.layer = 2
    tagtree.check(ctx)
    ctx.report.layers_run.append(2)
    if ctx.report.has_errors(layer=2):
        return ctx
    ctx.model = model.build(ctx.parsed)
    run_layer(ctx, 3)
    if ctx.report.has_errors(layer=3):
        return ctx
    run_layer(ctx, 4)
    return ctx
