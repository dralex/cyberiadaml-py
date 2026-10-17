#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The document metainformation test
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

ld = CyberiadaML.LocalDocument();
try:
    ld.open(sys.argv[0] + "-input.graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatQt, False);
    d = CyberiadaML.Document(ld)
    assert d.get_state_machines()[0].get_name() == "SM"
    assert d.get_meta().get_string("platform") == "Berloga"
    assert d.get_meta().get_string("platformVersion") == "1.4"
    assert d.get_meta().get_string("platformLanguage") == "script"
    assert d.get_meta().get_string("target") == "Unit"
    assert d.get_meta().get_string("name") == "Test document"
    assert d.get_meta().get_string("author") == "Author"
    assert d.get_meta().get_string("contact") == "platform@kruzhok.org"
    assert d.get_meta().get_string("description") == "1\n2\n3"
    assert d.get_meta().get_string("version") == "0.1"
    assert d.get_meta().get_string("date") == "2024-04-14T11:22:00"
    assert d.get_meta().get_string("markupLanguage") == "html"
    assert d.get_meta().transition_order == CyberiadaML.transitionOrderExit
    assert d.get_meta().event_propagation == CyberiadaML.docEventPropagationPropagate
    print(d)
    ld.open(sys.argv[0] + "-input2.graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatNone, False, False, True, True, True);
    d = CyberiadaML.Document(ld)
    assert d.get_meta().standard_version == "1.0"
    # the skipped metainformation is replaced by the default one
    assert d.get_meta().transition_order == CyberiadaML.transitionOrderAction
    assert d.get_meta().event_propagation == CyberiadaML.docEventPropagationBlock
    print(d)
except CyberiadaML.Exception as e:
    sys.stderr.write('Unexpected CyberiadaML exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
