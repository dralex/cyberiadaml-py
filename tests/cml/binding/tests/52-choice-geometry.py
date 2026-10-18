#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The choice pseudostate geometry update test
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


def rect_is(r, x, y, w, h):
    return (r.valid and abs(r.x - x) < 0.01 and abs(r.y - y) < 0.01 and
            abs(r.width - w) < 0.01 and abs(r.height - h) < 0.01)


try:
    d = CyberiadaML.LocalDocument()
    d.open(sys.argv[0] + "-input.graphml")
    sm = d.get_state_machines()[0]

    local = sm.find_element_by_id("n1::n0")
    assert local.has_geometry()
    assert rect_is(local.get_geometry_rect(), 0, 5, 100, 50)

    # the choice rect can be updated
    local.update_geometry(CyberiadaML.Rect(20, 30, 60, 40))
    assert rect_is(local.get_geometry_rect(), 20, 30, 60, 40)
    assert rect_is(local.get_bound_rect(d), 20, 30, 60, 40)

    # the update gives geometry to a choice without one
    bare = sm.find_element_by_id("n0")
    assert not bare.has_geometry()
    bare.update_geometry(CyberiadaML.Rect(-100, -50, 40, 40))
    assert bare.has_geometry()

    # both rects survive the save/reopen round trip
    saved = CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml")
    saved.save()
    d2 = CyberiadaML.LocalDocument()
    d2.open(sys.argv[0] + ".graphml")
    sm2 = d2.get_state_machines()[0]
    assert rect_is(sm2.find_element_by_id("n1::n0").get_geometry_rect(), 20, 30, 60, 40)
    assert rect_is(sm2.find_element_by_id("n0").get_geometry_rect(), -100, -50, 40, 40)
except CyberiadaML.Exception as e:
    sys.stderr.write('Unexpected CyberiadaML exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(2)
