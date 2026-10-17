#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  An XML exceptions test
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
    # broken XML markup
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-input.graphml")
        exit(1)
    except CyberiadaML.XMLException as e:
        assert str(e).startswith('XML Exception')

    # missing GraphML root node
    try:
        ld = CyberiadaML.LocalDocument()
        ld.open(sys.argv[0] + "-input2.graphml")
        exit(1)
    except CyberiadaML.XMLException:
        pass

    # decoding a non-XML buffer
    try:
        d = CyberiadaML.Document()
        d.decode("not an xml buffer")
        exit(1)
    except CyberiadaML.XMLException:
        pass

    # decoding an empty buffer
    try:
        d = CyberiadaML.Document()
        d.decode("")
        exit(1)
    except CyberiadaML.ParametersException:
        pass

    # encoding with the detect format
    try:
        d = CyberiadaML.Document()
        d.new_state_machine("SM")
        d.encode(CyberiadaML.formatDetect)
        exit(1)
    except CyberiadaML.ParametersException:
        pass

    # the legacy format supports single-SM documents only
    try:
        d = CyberiadaML.Document()
        d.new_state_machine("SM 1")
        d.new_state_machine("SM 2")
        d.encode(CyberiadaML.formatLegacyYED)
        exit(1)
    except CyberiadaML.ParametersException:
        pass

    # the results are returned: the format constants are not written back
    d = CyberiadaML.Document()
    d.new_state_machine("SM")
    d2 = CyberiadaML.Document()
    assert (d2.decode(d.encode(), CyberiadaML.formatDetect) ==
            (CyberiadaML.formatCyberiada10, "Cyberiada-GraphML-1.0"))
    assert int(CyberiadaML.formatDetect) == 99

    # the out-parameter forms are not bound
    for call in (lambda: d2.decode(d.encode(), CyberiadaML.formatDetect, ""),
                 lambda: d2.encode("")):
        try:
            call()
            exit(1)
        except TypeError:
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
