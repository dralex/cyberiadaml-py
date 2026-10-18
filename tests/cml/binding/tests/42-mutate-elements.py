#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The elements mutation test
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
    d = CyberiadaML.Document(CyberiadaML.geometryFormatQt)

    # the explicit id factories
    sm = d.new_state_machine("sm1", "SM")
    assert sm.get_id() == "sm1"
    s1 = d.new_state(sm, "s1", "State 1", CyberiadaML.Action(CyberiadaML.actionEntry, "init();"),
                     CyberiadaML.Rect(0, 0, 100, 50))
    s2 = d.new_state(sm, "s2", "State 2")
    init = d.new_initial(sm, "init1", "Init", CyberiadaML.Point(-10, -10))
    fin = d.new_final(sm, "fin1", "Fin", CyberiadaML.Point(200, 0))
    choice = d.new_choice(sm, "ch1", "Choice", CyberiadaML.Rect(50, 100, 20, 20))
    term = d.new_terminate(sm, "term1", "Term", CyberiadaML.Point(300, 0))
    assert init.get_id() == "init1"
    assert fin.get_id() == "fin1"
    assert choice.get_id() == "ch1"
    assert term.get_id() == "term1"
    t1 = d.new_transition(sm, CyberiadaML.transitionExternal, "t1", init, s1, CyberiadaML.Action())
    assert t1.get_id() == "t1"

    # duplicate identifiers are not allowed
    try:
        d.new_state(sm, "s1", "Duplicate")
        exit(1)
    except CyberiadaML.ParametersException:
        pass
    try:
        d.new_choice(sm, "ch1", "Duplicate")
        exit(1)
    except CyberiadaML.ParametersException:
        pass
    try:
        d.new_transition(sm, CyberiadaML.transitionExternal, "t1", s1, s2, CyberiadaML.Action())
        exit(1)
    except CyberiadaML.ParametersException:
        pass

    # the identifier change
    s2.set_id("s2x")
    assert d.find_element_by_id("s2x").get_id() == "s2x"
    assert d.find_element_by_id("s2") is None

    # the collapsed flag
    s1.set_collapsed(True)
    assert s1.is_collapsed()
    s1.set_collapsed(False)
    assert not s1.is_collapsed()

    # the region and element geometry updates
    s1.update_region_geometry_rect(CyberiadaML.Rect(0, 0, 90, 40))
    assert s1.has_region_geometry()
    s1.update_geometry(CyberiadaML.Rect(10, 10, 120, 60))
    assert s1.get_geometry_rect() == CyberiadaML.Rect(10, 10, 120, 60)

    # adding a child makes the state composite
    assert s1.is_simple_state()
    d.new_state(s1, "sub1", "Substate")
    assert s1.is_composite_state()

    # the transition updates
    t2 = d.new_transition(sm, CyberiadaML.transitionLocal, "t2", s1, s2,
                          CyberiadaML.Action("GO", "ready", "run();"))
    t2.update(CyberiadaML.Point(1, 2), CyberiadaML.Point(3, 4))
    assert t2.has_geometry_source_point()
    assert t2.has_geometry_target_point()
    pl = CyberiadaML.Polyline()
    pl.append(CyberiadaML.Point(5, 6))
    pl.append(CyberiadaML.Point(7, 8))
    t2.update(pl)
    assert t2.has_geometry_polyline()
    t2.update("s2x", "s1")
    assert t2.get_source_element_id() == "s2x"
    assert t2.get_target_element_id() == "s1"

    # the action updates
    a = t2.get_action()
    a.update("STOP", "", "halt();", CyberiadaML.eventPropagationBlock)
    assert a.get_trigger() == "STOP"
    assert a.get_propagation() == CyberiadaML.eventPropagationBlock
    a.update("finish();")
    assert a.get_behavior() == "finish();"

    print(d)
    CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml").save()

    # the removal flips the state back to simple
    s1.remove_element("sub1")
    assert s1.is_simple_state()
    assert sm.first_element().get_id() == "s1"

    # the action cleanup
    a.clear()
    assert not t2.has_action()

    # the collection cleanup
    sm.clear()
    assert sm.children_count() == 0
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
