#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  A transition test
# 
#  Copyright (C) 2025 Alexey Fedoseev <aleksey@fedoseev.net>
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
    parent1 = d.new_state(sm, "Parent 0")
    s1 = d.new_state(parent1, "State 0")
    s2 = d.new_state(parent1, "State 1")
    d.new_transition(sm, CyberiadaML.transitionExternal, s1, s2, CyberiadaML.Action())
    d.new_transition(sm, CyberiadaML.transitionExternal, s1, s2, CyberiadaML.Action("A"))
    try:
        # check id uniqueness
        d.new_transition(sm, CyberiadaML.transitionExternal, "n0::n0-n0::n1", s1, s2, CyberiadaML.Action())
    except CyberiadaML.ParametersException:
        pass
    try:
        # check sm-related transition
        d.new_transition(sm, CyberiadaML.transitionExternal, sm, s1, CyberiadaML.Action())
    except CyberiadaML.ParametersException:
        pass

    pl = CyberiadaML.Polyline()
    pl.append(CyberiadaML.Point(0, 0))
    pl.append(CyberiadaML.Point(5, 10))
    pl.append(CyberiadaML.Point(15, 20))
    t1 = d.new_transition(sm, CyberiadaML.transitionExternal, s1, s1, CyberiadaML.Action("IDLE"), pl,
                     CyberiadaML.Point(-1, -2), CyberiadaML.Point(3, 4))
    d.new_transition(sm, CyberiadaML.transitionExternal, parent1, s1, CyberiadaML.Action("INSIDE"),
                     CyberiadaML.Polyline(), CyberiadaML.Point(-1, -2), CyberiadaML.Point(3, 4))
    d.new_transition(sm, CyberiadaML.transitionExternal, s2, parent1, CyberiadaML.Action("OUTSIDE"),
                     CyberiadaML.Polyline(), CyberiadaML.Point(-1, -2), CyberiadaML.Point(3, 4), CyberiadaML.Point(5, 6))
    try:
        # check transition action
        d.new_transition(sm, CyberiadaML.transitionExternal, s1, s2, CyberiadaML.Action(CyberiadaML.actionEntry, "init();"))
    except CyberiadaML.ParametersException:
        pass
    
    parent2 = d.new_state(sm, "Parent 1")
    t2 = d.new_transition(sm, CyberiadaML.transitionExternal, s2, parent2, CyberiadaML.Action("EVENT", "guard()", "action();"))

    print(d)
    CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml").save()

    f = t1.compare_actions(t2)
    assert not (f & CyberiadaML.adiffArguments)
    assert not (f & CyberiadaML.adiffOrder)
    assert not (f & CyberiadaML.adiffGuards)
    assert f & CyberiadaML.adiffActions
    assert not (f & CyberiadaML.adiffNumber)
    assert not (f & CyberiadaML.adiffTypes)
    
except CyberiadaML.Exception as e:
    sys.stderr.write('Unexpected CyberiadaML exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
