#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  A format exceptions test
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
    # a state action not matching the action grammar
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-input.graphml")
        exit(1)
    except CyberiadaML.CybMLException as e:
        assert str(e).startswith('CyberiadaML Exception')

    # an edge action not matching the action grammar
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-input2.graphml")
        exit(1)
    except CyberiadaML.CybMLException:
        pass

    # a metainformation line without the separator
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-input3.graphml")
        exit(1)
    except CyberiadaML.MetainfoException:
        pass

    # an unsupported version of the standard
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-input4.graphml")
        exit(1)
    except CyberiadaML.MetainfoException:
        pass
except CyberiadaML.Exception as e:
    sys.stderr.write('Unexpected CyberiadaML exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
