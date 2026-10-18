#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The Qt geometry round trip test: a state machine without a rect keeps its global coordinates
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

def same_point(p1, p2):
    return abs(p1.x - p2.x) < 0.001 and abs(p1.y - p2.y) < 0.001

# the content is not centred on the origin on purpose: a frame taken from
# the content would move it on the way through the file
try:
    d = CyberiadaML.Document()
    sm = d.new_state_machine("SM")
    working = d.new_state(sm, "Working", CyberiadaML.Action(), CyberiadaML.Rect(10, 20, 200, 100))
    parent = d.new_state(sm, "Parent", CyberiadaML.Action(), CyberiadaML.Rect(-300, -200, 400, 300))
    initial = d.new_initial(parent, CyberiadaML.Point(-40, -40))
    final = d.new_final(sm, CyberiadaML.Point(300, 100))
    before = sm.get_bound_rect(d)

    buffer = d.encode()
    d1 = CyberiadaML.Document()
    d1.decode(buffer, CyberiadaML.formatDetect, CyberiadaML.geometryFormatQt)

    sm1 = d1.get_state_machines()[0]
    assert sm1.get_bound_rect(d1).almost_equal(before)
    w1 = d1.find_element_by_id(working.get_id())
    p1 = d1.find_element_by_id(parent.get_id())
    i1 = d1.find_element_by_id(initial.get_id())
    f1 = d1.find_element_by_id(final.get_id())
    assert w1 is not None and p1 is not None and i1 is not None and f1 is not None
    assert w1.get_geometry_rect().almost_equal(working.get_geometry_rect())
    assert p1.get_geometry_rect().almost_equal(parent.get_geometry_rect())
    assert same_point(i1.get_geometry_point(), initial.get_geometry_point())
    assert same_point(f1.get_geometry_point(), final.get_geometry_point())

    # and the round trip is stable: a second one changes nothing either
    assert d1.encode() == buffer
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
