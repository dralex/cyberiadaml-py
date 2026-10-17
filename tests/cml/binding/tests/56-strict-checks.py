#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The strict standard checks test
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


# load the diagram and report whether the library accepted it
def loaded(path, strict):
    try:
        d = CyberiadaML.LocalDocument()
        d.open(path, CyberiadaML.formatCyberiada10, CyberiadaML.geometryFormatNone,
               False, False, False, False, False, strict)
    except CyberiadaML.CybMLException:
        return False
    return True


try:
    prefix = sys.argv[0] + "-"

    # the optional requirements are checked in the strict mode only
    for name in ("bad-id-char", "no-marker", "no-sm-name", "vertex-not-first"):
        path = prefix + name + ".graphml"
        assert loaded(path, False)
        assert not loaded(path, True)

    # the mandatory requirements are checked in any mode
    assert not loaded(prefix + "foreign-tag.graphml", False)
    assert not loaded(prefix + "foreign-tag.graphml", True)

    # the conforming document is read in the strict mode
    assert loaded(prefix + "two-machines.graphml", False)
    assert loaded(prefix + "two-machines.graphml", True)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
