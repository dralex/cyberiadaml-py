#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  A bound rect test (based on Qt geometry)
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
    d.new_state(sm, "A", CyberiadaML.Action(), CyberiadaML.Rect(0, 50, 100, 25))
    s = d.new_state(sm, "B", CyberiadaML.Action(), CyberiadaML.Rect(-100, -250, 100, 200))
    d.new_state(s, "B2", CyberiadaML.Action(), CyberiadaML.Rect(0, 50, 50, 50))
    d.new_initial(s, CyberiadaML.Point(0, 0))
    d.new_state(sm, "C", CyberiadaML.Action(), CyberiadaML.Rect(-50, 0, 1000, 100))
    br = d.get_bound_rect()
    assert br == CyberiadaML.Rect(-50, -143.75, 1000, 412.5)
except CyberiadaML.Exception as e:
    sys.stderr.write('Unexpected CyberiadaML exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
