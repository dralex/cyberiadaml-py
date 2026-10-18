#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The geometry update test: the drawn elements stay
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
    # a reconstructed document, then one state stripped of its geometry and
    # updated: the others keep their places, the stripped one joins the flow
    d = CyberiadaML.LocalDocument()
    d.open(sys.argv[0] + "-input.graphml")
    d.reconstruct_geometry(True)
    d.round_geometry()
    sm = d.get_state_machines()[0]
    before = {}
    for e in sm.get_children():
        if e.get_type() in (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState):
            r = e.get_geometry_rect()
            before[e.get_id()] = (r.x, r.y, r.width, r.height)
    sm.find_element_by_id("n1").clean_geometry()
    d.update_geometry(True)
    d.round_geometry()
    sm = d.get_state_machines()[0]
    # the machine may grow (its centre moves the Qt coordinates), so the
    # drawn states are checked by their sizes and the composite by its content
    kept = True
    for e in sm.get_children():
        if e.get_id() in before and e.get_id() != "n1":
            r = e.get_geometry_rect()
            kept = kept and (r.width, r.height) == before[e.get_id()][2:]
    inner = [(c.get_id(), c.get_geometry_rect().x, c.get_geometry_rect().y)
             for c in sm.find_element_by_id("n0").get_children()
             if c.get_type() == CyberiadaML.elementSimpleState]
    print("the drawn states keep their sizes:", int(kept))
    print("the composite content:", inner)
    print("the stripped state placed:", int(sm.find_element_by_id("n1").has_geometry()))
    print("check:", int(d.check_geometry()))
    print(d)
except Exception:
    traceback.print_exc()
    sys.exit(1)
