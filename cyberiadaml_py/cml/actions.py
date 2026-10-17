# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The actions of the CyberiadaML interface
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
"""The action of a state or a transition."""
from .enums import (ActionType, EventPropagation, actionEntry, actionExit,
                    actionTransition, eventPropagationNone)

ENTRY = 'entry'
EXIT = 'exit'
PROPAGATION_NAMES = {
    EventPropagation.eventPropagationBlock: 'block',
    EventPropagation.eventPropagationPropagate: 'propagate',
    EventPropagation.eventPropagationDefer: 'defer',
}


class Action:
    """An entry/exit activity or a (internal) transition action.

    Action(type, behavior='') or
    Action(trigger='', guard='', behavior='', propagation=None).
    """

    def __init__(self, *args, **kwargs) -> None:
        self._type = actionTransition
        self._trigger = self._guard = self._behavior = ''
        self._propagation = eventPropagationNone
        if (args and isinstance(args[0], ActionType)) or 'type' in kwargs:
            names = ('type', 'behavior')
            values = dict(zip(names, args), **kwargs)
            self._type = ActionType(values['type'])
            self._behavior = values.get('behavior', '')
        else:
            fields = ('trigger', 'guard', 'behavior', 'propagation')
            values = dict(zip(fields, args), **kwargs)
            self._trigger = values.get('trigger', '')
            self._guard = values.get('guard', '')
            self._behavior = values.get('behavior', '')
            self._propagation = EventPropagation(
                values.get('propagation', eventPropagationNone))

    def get_type(self) -> ActionType:
        return self._type

    def is_empty_transition(self) -> bool:
        return self._type == actionTransition and not self._trigger and \
            not self._guard and not self._behavior

    def has_trigger(self) -> bool:
        return bool(self._trigger)

    def get_trigger(self) -> str:
        return self._trigger

    def has_guard(self) -> bool:
        return bool(self._guard)

    def get_guard(self) -> str:
        return self._guard

    def has_behavior(self) -> bool:
        return bool(self._behavior)

    def get_behavior(self) -> str:
        return self._behavior

    def has_propagation(self) -> bool:
        return self._propagation != eventPropagationNone

    def get_propagation(self) -> EventPropagation:
        return self._propagation

    def update(self, *args, **kwargs) -> None:
        if (len(args) == 1 and not kwargs) or \
                (not args and set(kwargs) == {'behavior'}):
            self._behavior = args[0] if args else kwargs['behavior']
            return
        names = ('trigger', 'guard', 'behavior', 'propagation')
        values = dict(zip(names, args), **kwargs)
        if self._type == actionTransition and not any(
                values.get(name) for name in names[:3]):
            return  # the C++ refuses a fully empty transition action
        self._trigger = values.get('trigger', '')
        self._guard = values.get('guard', '')
        self._behavior = values.get('behavior', '')
        self._propagation = EventPropagation(
            values.get('propagation', eventPropagationNone))

    def clear(self) -> None:
        if self._type == actionTransition:
            self._trigger = self._guard = self._behavior = ''
            self._propagation = eventPropagationNone
        else:
            self._guard = self._behavior = ''

    def copy(self) -> 'Action':
        result = Action()
        result.__dict__.update(self.__dict__)
        return result

    def __repr__(self) -> str:
        parts = []
        if self._type == actionEntry:
            parts.append(ENTRY)
        elif self._type == actionExit:
            parts.append(EXIT)
        elif self._trigger:
            parts.append("trigger: '%s'" % self._trigger)
        if self._propagation != eventPropagationNone:
            parts.append("propagation: '%s'" %
                         PROPAGATION_NAMES[self._propagation])
        if self._guard:
            parts.append("guard: '%s'" % self._guard)
        if self._behavior:
            parts.append("behavior: '%s'" % self._behavior)
        return ', '.join(parts)
