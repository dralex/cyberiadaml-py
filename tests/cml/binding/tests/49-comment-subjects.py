#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The comment subjects test
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
    d = CyberiadaML.LocalDocument()
    d.open(sys.argv[0] + "-input.graphml")

    sm = d.get_state_machines()[0]

    # the subject edges are imported into the comment
    note = sm.find_element_by_id("n2")
    assert note
    assert note.get_type() == CyberiadaML.elementComment
    assert note.has_subjects()
    subjects = note.get_subjects()
    assert len(subjects) == 3
    assert subjects[0].get_type() == CyberiadaML.commentSubjectElement
    assert not subjects[0].has_fragment()
    assert subjects[0].get_element().get_id() == "n0"
    assert subjects[1].get_type() == CyberiadaML.commentSubjectName
    assert subjects[1].get_fragment() == "Second"
    assert subjects[1].get_element().get_id() == "n1"
    assert subjects[2].get_type() == CyberiadaML.commentSubjectData
    assert subjects[2].get_fragment() == "run"
    assert subjects[2].get_element().get_id() == "n0"

    print(CyberiadaML.Document(d))

    # the subjects survive the save/load round trip
    CyberiadaML.LocalDocument(d, sys.argv[0] + ".graphml").save()
    d2 = CyberiadaML.LocalDocument()
    d2.open(sys.argv[0] + ".graphml")
    note2 = d2.get_state_machines()[0].find_element_by_id("n2")
    assert note2
    assert len(note2.get_subjects()) == 3

    # removal by index works for an element-type subject
    note2.remove_subject(0)
    assert len(note2.get_subjects()) == 2
    assert note2.get_subjects()[0].get_type() == CyberiadaML.commentSubjectName
    try:
        note2.remove_subject(2)
        exit(1)
    except CyberiadaML.ParametersException:
        pass
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
