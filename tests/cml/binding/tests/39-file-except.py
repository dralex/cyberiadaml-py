#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  A file exceptions test
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
    # opening a nonexistent file
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-nonexistent.graphml")
        exit(1)
    except CyberiadaML.FileException as e:
        assert str(e).startswith('File Exception')

    # opening an empty file
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-empty.graphml")
        exit(1)
    except CyberiadaML.FileException:
        pass

    # saving to an unavailable path
    try:
        d = CyberiadaML.Document()
        d.new_state_machine("SM")
        ld = CyberiadaML.LocalDocument(d, "/nonexistent-dir/out.graphml")
        ld.save()
        exit(1)
    except CyberiadaML.FileException:
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
