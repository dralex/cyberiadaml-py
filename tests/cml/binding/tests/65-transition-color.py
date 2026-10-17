#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
#
#  The transition color is saved without the transition geometry
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
    # a colored transition without any geometry keeps its color on saving
    t = d.new_transition(sm, CyberiadaML.transitionExternal, a, b,
                         CyberiadaML.Action("GO"), color="#00CC44")
    path = sys.argv[0] + ".graphml"
    CyberiadaML.LocalDocument(d, path).save()
    reloaded = CyberiadaML.LocalDocument()
    reloaded.open(path)
    rt = reloaded.find_element_by_id(t.get_id())
    assert rt.has_color() and rt.get_color() == "#00CC44", "the transition color is lost"
    print(reloaded)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
