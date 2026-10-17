#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The comment subjects on transitions test
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
    # the comment subject refers to a transition (8.5)
    d = CyberiadaML.LocalDocument()
    d.open(sys.argv[0] + "-input.graphml", CyberiadaML.formatCyberiada10,
           CyberiadaML.geometryFormatNone)
    sm = d.get_state_machines()[0]
    note = sm.find_element_by_id("n2")
    assert note
    assert len(note.get_subjects()) == 1
    subject = note.get_subjects()[0]
    assert subject.get_type() == CyberiadaML.commentSubjectElement
    assert subject.get_element().get_type() == CyberiadaML.elementTransition
    assert subject.get_element().get_id() == "t0"
    print(CyberiadaML.Document(d))

    # the edge order in the document does not matter
    d2 = CyberiadaML.LocalDocument()
    d2.open(sys.argv[0] + "-input2.graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatNone)
    note2 = d2.get_state_machines()[0].find_element_by_id("n2")
    assert note2
    assert note2.get_subjects()[0].get_element().get_id() == "t0"

    # a new subject may be attached to a transition as well
    new_note = d.new_comment(sm, "A second note")
    transition = sm.find_element_by_id("t0")
    assert transition
    d.add_comment_to_element(new_note, transition)
    assert len(new_note.get_subjects()) == 1

    # the links survive the save/load round trip
    CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml").save()
    d3 = CyberiadaML.LocalDocument()
    d3.open(sys.argv[0] + ".graphml", CyberiadaML.formatCyberiada10,
            CyberiadaML.geometryFormatNone)
    sm3 = d3.get_state_machines()[0]
    note3 = sm3.find_element_by_id("n2")
    assert note3
    assert note3.get_subjects()[0].get_element().get_id() == "t0"
    # the isomorphism check ignores the comments: the C library compares the node targets only
    assert sm.check_isomorphism(sm3, True) == CyberiadaML.smiIdentical
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
