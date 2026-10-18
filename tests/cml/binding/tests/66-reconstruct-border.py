#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
#
#  The reconstruction border test: the wide labels fit the machine border
#
#  Copyright (C) 2024 Alexey Fedoseev <aleksey@fedoseev.net>
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
    # the full reconstruction keeps the wide transition labels inside the
    # machine border, and the geometry check reads the Qt-format label rects
    # by their centre
    d = CyberiadaML.Document()
    sm = d.new_state_machine("Bomb")
    init = d.new_initial(sm)
    setting = d.new_state(sm, "Setting")
    timing = d.new_state(sm, "Timing")
    d.new_transition(sm, CyberiadaML.transitionExternal, init, setting,
                     CyberiadaML.Action("", "", "timeout = INIT_TIMEOUT"))
    d.new_transition(sm, CyberiadaML.transitionExternal, setting, timing,
                     CyberiadaML.Action("ARM", "", "code = 0"))
    d.new_transition(sm, CyberiadaML.transitionExternal, timing, setting,
                     CyberiadaML.Action("ARM", "code == defuse", "show(code); reset(timer)"))
    d.reconstruct_geometry(True)
    print("check after the reconstruction:", int(d.check_geometry()))
    print(d)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
