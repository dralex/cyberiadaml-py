#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The state hierarchy test
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

    parent1 = d.new_state(sm, "Parent 0")
    try:
	# check id uniqueness
        d.new_state(sm, "n0", "test")
    except CyberiadaML.ParametersException:
        pass
    try:
	# check non-empty name
        d.new_state(sm, "")
    except CyberiadaML.ParametersException:
        pass
	
    assert parent1.is_simple_state()
    d.new_state(parent1, "State 0-0")
    assert parent1.is_composite_state()

    subparent = d.new_state(parent1, "Subparent 0-1")
    d.new_state(subparent, "State 0-1-0")
    d.new_state(subparent, "State 0-1-1")
	
    parent2 = d.new_state(sm, "Parent 1")
    d.new_state(parent2, "State 1-0")
    ch = d.new_state(parent2, "State 1-1")

    assert ch.get_qualified_name() == "Parent 1::State 1-1"
    assert ch.get_full_qualified_name() == "SM::Parent 1::State 1-1"
    
    try:
	# check id uniqueness on the deep level
        d.new_state(parent2, "n1::n1", "test")
    except CyberiadaML.ParametersException:
        pass

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
