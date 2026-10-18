#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The edge label and comment subject bound rect test
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
    # a transition label rect outside the node extents loads without
    # the bound rect mismatch and extends the document bound rect
    d = CyberiadaML.LocalDocument()
    d.open(sys.argv[0] + "-input.graphml")
    br = d.get_bound_rect()
    assert br.valid
    assert abs(br.width - 1000.0) < 0.01
    assert abs(br.height - 760.0) < 0.01
    t = d.get_state_machines()[0].find_element_by_id("n0-n1")
    assert t.has_geometry_label_rect()

    # a subject edge polyline agrees between the libraries...
    s1 = CyberiadaML.LocalDocument()
    s1.open(sys.argv[0] + "-input2.graphml")
    c1 = s1.get_state_machines()[0].find_element_by_id("cX")
    assert c1.has_subjects()

    # ...with a geometry-less comment as well
    s2 = CyberiadaML.LocalDocument()
    s2.open(sys.argv[0] + "-input3.graphml")
    c2 = s2.get_state_machines()[0].find_element_by_id("cX")
    assert not c2.has_geometry()
    assert c2.has_subjects()
except CyberiadaML.Exception as e:
    sys.stderr.write('Unexpected CyberiadaML exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(2)
