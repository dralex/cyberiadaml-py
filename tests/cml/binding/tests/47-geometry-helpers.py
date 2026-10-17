#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The geometry and string helpers test
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
    # the point helpers
    p_invalid = CyberiadaML.Point()
    assert repr(p_invalid) == "()"
    p_invalid.round()
    assert not p_invalid.valid
    p = CyberiadaML.Point(1.25, 2.75)
    assert repr(p) == "(1.25; 2.75)"
    p.round()
    assert repr(p) == "(1; 2)"

    # the rect helpers
    r_invalid = CyberiadaML.Rect()
    assert repr(r_invalid) == "()"
    r_invalid.round()
    assert not r_invalid.valid
    r1 = CyberiadaML.Rect(0, 0, 10, 10)
    r2 = CyberiadaML.Rect(0, 0, 10, 10)
    assert r1 == r2
    r3 = CyberiadaML.Rect(0, 0, 10.0005, 10)
    assert r1 != r3
    assert r1.almost_equal(r3)
    assert r_invalid.almost_equal(CyberiadaML.Rect())
    assert not r_invalid.almost_equal(r1)
    assert not r1.almost_equal(r_invalid)
    assert r1 != r_invalid
    r4 = CyberiadaML.Rect(1.25, 1.75, 2.25, 2.75)
    r4.round()
    assert r4 == CyberiadaML.Rect(1, 1, 2, 2)

    # the polyline helpers
    pl = CyberiadaML.Polyline()
    pl.append(CyberiadaML.Point(1.25, 2.75))
    pl.append(CyberiadaML.Point(3.25, 4.75))
    assert repr(pl) == "[ (1.25; 2.75), (3.25; 4.75) ]"
    pl.round()
    assert repr(pl) == "[ (1; 2), (3; 4) ]"

    # the rect expansion with the qt geometry (centered coordinates)
    dq = CyberiadaML.Document(CyberiadaML.geometryFormatQt)
    e1 = CyberiadaML.Rect(0, 0, 10, 10)
    e1.expand(CyberiadaML.Point(), dq)
    assert e1 == CyberiadaML.Rect(0, 0, 10, 10)
    e1.expand(CyberiadaML.Point(10, 0), dq)
    assert e1.almost_equal(CyberiadaML.Rect(2.5, 0, 15, 10))
    e1.expand(CyberiadaML.Rect(-20, 0, 2, 2), dq)
    assert e1.almost_equal(CyberiadaML.Rect(-5.5, 0, 31, 10))
    e3 = CyberiadaML.Rect()
    e3.expand(CyberiadaML.Point(5, 5), dq)
    assert e3.almost_equal(CyberiadaML.Rect(5, 5, 0, 0))
    e4 = CyberiadaML.Rect()
    e4.expand(CyberiadaML.Rect(1, 2, 3, 4), dq)
    assert e4 == CyberiadaML.Rect(1, 2, 3, 4)

    # the rect expansion with the cyberiada geometry (left-top coordinates)
    dc = CyberiadaML.Document(CyberiadaML.geometryFormatCyberiada10)
    e2 = CyberiadaML.Rect(0, 0, 10, 10)
    e2.expand(CyberiadaML.Point(15, -5), dc)
    assert e2.almost_equal(CyberiadaML.Rect(0, -5, 15, 15))
    e2.expand(CyberiadaML.Rect(20, 20, 5, 5), dc)
    assert e2.almost_equal(CyberiadaML.Rect(0, -5, 25, 30))
    pl2 = CyberiadaML.Polyline()
    pl2.append(CyberiadaML.Point(30, 0))
    pl2.append(CyberiadaML.Point(-10, -10))
    e2.expand(pl2, dc)
    assert e2.almost_equal(CyberiadaML.Rect(-10, -10, 40, 35))

    # the action strings
    assert repr(CyberiadaML.Action()) == ""
    assert repr(CyberiadaML.Action("EVENT", "g", "b();")) == "trigger: 'EVENT', guard: 'g', behavior: 'b();'"
    assert repr(CyberiadaML.Action(CyberiadaML.actionEntry, "init();")) == "entry, behavior: 'init();'"
    assert repr(CyberiadaML.Action(CyberiadaML.actionExit)) == "exit"
    assert (repr(CyberiadaML.Action("EV", "", "b();", CyberiadaML.eventPropagationDefer)) ==
            "trigger: 'EV', propagation: 'defer', behavior: 'b();'")

    # a transition action may be updated to guard-only or behaviour-only
    # (a choice branch, an initial/completion edge); only a fully empty
    # update is refused
    tr = CyberiadaML.Action("EVENT", "", "b();")
    tr.update("", "g", "c();")
    assert tr.get_trigger() == "" and tr.get_guard() == "g" and tr.get_behavior() == "c();"
    tr.update("", "", "")
    assert tr.get_behavior() == "c();"

    # guards are not allowed in the entry/exit activities
    d = CyberiadaML.Document(CyberiadaML.geometryFormatQt)
    sm = d.new_state_machine("sm1", "SM")
    s1 = d.new_state(sm, "s1", "State 1")
    bad = CyberiadaML.Action(CyberiadaML.actionEntry, "b();")
    bad.update("entry", "guard", "b();")
    try:
        s1.add_action(bad)
        exit(1)
    except CyberiadaML.ParametersException:
        pass

    # the geometry cleanup cascade
    s2 = d.new_state(sm, "s2", "State 2", CyberiadaML.Action(),
                     CyberiadaML.Rect(0, 0, 50, 50), CyberiadaML.Rect(0, 0, 40, 40))
    d.new_state(s2, "sub1", "Substate", CyberiadaML.Action(), CyberiadaML.Rect(0, 0, 10, 10))
    init = d.new_initial(sm, CyberiadaML.Point(-10, 0))
    d.new_final(sm, CyberiadaML.Point(100, 0))
    d.new_choice(sm, CyberiadaML.Rect(50, 50, 20, 20))
    d.new_terminate(sm, CyberiadaML.Point(120, 0))
    cm = d.new_comment(sm, "A comment", CyberiadaML.Rect(150, 0, 60, 30))
    d.add_comment_to_element(cm, s2, CyberiadaML.Point(0, 0), CyberiadaML.Point(10, 10))
    pl3 = CyberiadaML.Polyline()
    pl3.append(CyberiadaML.Point(0, 0))
    pl3.append(CyberiadaML.Point(5, 5))
    d.new_transition(sm, CyberiadaML.transitionExternal, init, s2, CyberiadaML.Action(),
                     pl3, CyberiadaML.Point(0, 0), CyberiadaML.Point(1, 1))
    assert d.has_geometry()
    d.clean_geometry()
    assert not d.has_geometry()
    assert d.get_geometry_format() == CyberiadaML.geometryFormatNone
    assert not s2.has_geometry()
    assert not s2.has_region_geometry()
    assert not init.has_geometry()
    assert not cm.has_geometry()
    assert not cm.get_subjects()[0].has_geometry()
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
