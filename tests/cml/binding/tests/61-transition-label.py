#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The transition label geometry setter and the triggerless action test
# 
#  Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
# 
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see https://www.gnu.org/licenses/
#  ----------------------------------------------------------------------------- 

import sys
import traceback
import CyberiadaML

try:
    d = CyberiadaML.Document()
    sm = d.new_state_machine("SM")
    a = d.new_state(sm, "A")
    b = d.new_state(sm, "B")
    t = d.new_transition(sm, CyberiadaML.transitionExternal, a, b,
                         CyberiadaML.Action(CyberiadaML.actionTransition))

    # the label point setter: set, then clear (an invalid point resets it)
    assert not t.has_geometry_label_point()
    t.update_label(CyberiadaML.Point(12, -8))
    assert t.has_geometry_label_point()
    assert t.get_geometry_label_point().x == 12 and t.get_geometry_label_point().y == -8
    t.update_label(CyberiadaML.Point())
    assert not t.has_geometry_label_point()

    # a transition action may be guard-only or behaviour-only, not only
    # trigger-bearing; only a fully empty one is refused
    t.get_action().update("", "x > 0", "")
    assert t.get_action().get_guard() == "x > 0"
    t.get_action().update("", "", "run()")
    assert t.get_action().get_behavior() == "run()"
    assert not t.get_action().has_trigger() and not t.get_action().has_guard()
    t.get_action().update("", "", "")
    assert t.get_action().get_behavior() == "run()"
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
