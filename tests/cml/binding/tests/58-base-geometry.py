#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The base (short) geometry format test
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

EPS = 0.01

STATES = [CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState]


# the loose rect size is derived on load: no state is left without one
def check_sizes(d):
    states = d.find_elements_by_types(STATES)
    assert states
    for s in states:
        assert s.has_geometry()
        r = s.get_geometry_rect()
        assert r.valid
        assert r.width > 0.0 and r.height > 0.0


def state_rect(d, element_id):
    e = d.find_element_by_id(element_id)
    assert e
    return e.get_geometry_rect()


try:
    # the robot-vacuum example of the standard is authored in the base format
    d = CyberiadaML.LocalDocument()
    d.open(sys.argv[0] + "-input.graphml", CyberiadaML.formatCyberiada10,
           CyberiadaML.geometryFormatCyberiada10)
    assert d.meta().get_geometry() == CyberiadaML.geometryDeclarationShort
    check_sizes(d)
    # the content of the composite fits it
    assert d.check_geometry()

    # the corners the file authored are kept, the sizes are derived
    r = state_rect(d, "n0::n1")
    assert abs(r.x - 50.0) < EPS and abs(r.y - 100.0) < EPS
    r = state_rect(d, "n0::n2")
    assert abs(r.x - 50.0) < EPS and abs(r.y - 550.0) < EPS
    r = state_rect(d, "n0")
    assert abs(r.x - 800.0) < EPS and abs(r.y - 0.0) < EPS
    assert r.width >= 350.0 and r.height >= 750.0
    print(CyberiadaML.Document(d))

    # the declaration and the derived sizes survive the round trip
    CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml").save()
    d1 = CyberiadaML.LocalDocument()
    d1.open(sys.argv[0] + ".graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatCyberiada10)
    assert d1.meta().get_geometry() == CyberiadaML.geometryDeclarationShort
    check_sizes(d1)
    assert d1.get_state_machines()[0].check_isomorphism(d.get_state_machines()[0]) == \
        CyberiadaML.smiIdentical

    # the shrunk appendix Г.4 example
    d2 = CyberiadaML.LocalDocument()
    d2.open(sys.argv[0] + "-input2.graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatCyberiada10)
    assert d2.meta().get_geometry() == CyberiadaML.geometryDeclarationShort
    check_sizes(d2)
    assert d2.check_geometry()
    r = state_rect(d2, "node-0-0-1")
    assert abs(r.x - 50.0) < EPS and abs(r.y - 90.0) < EPS
    print(CyberiadaML.Document(d2))

    # the declaration is written, replaced and removed
    d3 = CyberiadaML.Document()
    d3.new_state_machine("sm", "SM")
    assert d3.meta().get_geometry() == CyberiadaML.geometryDeclarationAbsent
    d3.meta().set_geometry(CyberiadaML.geometryDeclarationFull)
    assert d3.encode().find("geometry/ full") != -1
    d3.meta().set_geometry(CyberiadaML.geometryDeclarationNone)
    assert d3.meta().get_geometry() == CyberiadaML.geometryDeclarationNone
    d3.meta().set_geometry(CyberiadaML.geometryDeclarationAbsent)
    assert d3.meta().get_geometry() == CyberiadaML.geometryDeclarationAbsent
    assert d3.encode().find("geometry/") == -1
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
