#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  A comment element test
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
    comm = d.new_comment(sm, "Top level")
    try:
        # check id uniqueness
        d.new_comment(sm, "n0", "testname", "Testbody");
    except CyberiadaML.ParametersException:
        pass
    
    state = d.new_state(sm, "State", CyberiadaML.Action(CyberiadaML.actionEntry, "action();"))
    comm2 = d.new_comment(state, "Comment inside a state\nwith two lines")
    d.new_formal_comment(sm, "Name", "Named formal comment", CyberiadaML.Rect(0, 5, 100, 50))

    d.add_comment_to_element(comm, state)
    d.add_comment_to_element_name(comm2, state, "S", CyberiadaML.Point(-1, -2), CyberiadaML.Point(3, 4))

    pl = CyberiadaML.Polyline([CyberiadaML.Point(0, 0), CyberiadaML.Point(5, 10), CyberiadaML.Point(15, 20)])
    d.add_comment_to_element_body(comm2, state, "action", CyberiadaML.Point(), CyberiadaML.Point(), pl)
    
    print(d)
    CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml").save()

except CyberiadaML.Exception as e:
    sys.stderr.write('Unexpected CyberiadaML exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
