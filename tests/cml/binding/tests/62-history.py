#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The history pseudostates test
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
    parent = d.new_state(sm, "State")
    # a history pseudostate belongs to a composite state's region
    d.new_shallow_history(parent, "Shallow", CyberiadaML.Point(10, 20))
    d.new_deep_history(parent, "Deep", CyberiadaML.Point(30, 40))

    # check id uniqueness and non-empty name
    refused = False
    try:
        d.new_shallow_history(parent, "n0", "name")
    except CyberiadaML.ParametersException:
        refused = True
    assert refused

    path = sys.argv[0] + ".graphml"
    print(d)
    CyberiadaML.LocalDocument(d, path).save()
    # the saved document reloads with the history tokens intact
    reloaded = CyberiadaML.LocalDocument()
    reloaded.open(path)
    print(reloaded)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
