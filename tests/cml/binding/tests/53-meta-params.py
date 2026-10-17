#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The optional metainformation parameters test
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
    # the absent parameters are not restored on load
    d = CyberiadaML.LocalDocument()
    d.open(sys.argv[0] + "-input.graphml", CyberiadaML.formatCyberiada10,
           CyberiadaML.geometryFormatNone)
    assert d.meta().transition_order == CyberiadaML.transitionOrderNone
    assert d.meta().event_propagation == CyberiadaML.docEventPropagationNone
    print(CyberiadaML.Document(d))

    # ... and are not added to the saved document
    CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml").save()
    d1 = CyberiadaML.LocalDocument()
    d1.open(sys.argv[0] + ".graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatNone)
    assert d1.meta().transition_order == CyberiadaML.transitionOrderNone
    assert d1.meta().event_propagation == CyberiadaML.docEventPropagationNone

    # the legacy transitionFirst value is read as the action order
    d2 = CyberiadaML.LocalDocument()
    d2.open(sys.argv[0] + "-input2.graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatNone)
    assert d2.meta().transition_order == CyberiadaML.transitionOrderAction
    assert d2.meta().event_propagation == CyberiadaML.docEventPropagationPropagate
    # the standard value is written back
    buffer = d2.encode()
    assert buffer.find("transitionOrder/ actionFirst") != -1
    assert buffer.find("transitionFirst") == -1

    # a single parameter survives the round trip
    d3 = CyberiadaML.LocalDocument()
    d3.open(sys.argv[0] + "-input3.graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatNone)
    assert d3.meta().transition_order == CyberiadaML.transitionOrderExit
    assert d3.meta().event_propagation == CyberiadaML.docEventPropagationNone
    print(CyberiadaML.Document(d3))

    # a document created from scratch carries both parameters
    d4 = CyberiadaML.Document()
    d4.new_state_machine("sm", "SM")
    assert d4.meta().transition_order == CyberiadaML.transitionOrderAction
    assert d4.meta().event_propagation == CyberiadaML.docEventPropagationBlock
    buffer = d4.encode()
    assert buffer.find("transitionOrder/ actionFirst") != -1
    assert buffer.find("eventPropagation/ block") != -1
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
