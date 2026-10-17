#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The copied comment subjects test: the copy points into itself
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

import gc
import sys
import traceback
import CyberiadaML

try:
    ld = CyberiadaML.LocalDocument()
    ld.open(sys.argv[0] + "-input.graphml")
    sm = ld.get_state_machines()[0]
    state = sm.find_elements_by_type(CyberiadaML.elementSimpleState)[0]
    comment = ld.new_comment(sm, "A note")
    ld.add_comment_to_element(comment, state)
    ld.add_comment_to_element_name(comment, state, state.get_name())
    ld.add_comment_to_element_body(comment, state, "entry")
    state_id = state.get_id()
    comment_id = comment.get_id()

    # the copies point into themselves: the original may go
    d1 = CyberiadaML.Document(ld)
    ld2 = CyberiadaML.LocalDocument(ld)
    e3 = ld.copy(None)
    del sm, state, comment
    del ld
    gc.collect()

    for d in (d1, ld2, e3):
        own_state = d.find_element_by_id(state_id)
        own_comment = d.find_element_by_id(comment_id)
        assert own_state is not None and own_comment is not None
        subjects = own_comment.get_subjects()
        assert len(subjects) == 3
        for i in range(len(subjects)):
            assert subjects[i].get_element() is own_state
        assert d.encode()
    del d, own_state, own_comment, subjects
    print(d1)

    # a subtree copy keeps the targets outside it and re-binds those inside
    composite = d1.find_elements_by_type(CyberiadaML.elementCompositeState)[0]
    inner = composite.find_elements_by_type(CyberiadaML.elementSimpleState)[0]
    outer = d1.find_element_by_id(state_id)
    assert outer.get_parent() is not composite
    nested = d1.new_comment(composite, "A nested note")
    d1.add_comment_to_element(nested, inner)
    d1.add_comment_to_element(nested, outer)
    copied = composite.copy(composite.get_parent())
    copied_note = copied.find_element_by_id(nested.get_id())
    assert copied_note is not None
    assert copied_note.get_subjects()[0].get_element() is copied.find_element_by_id(inner.get_id())
    assert copied_note.get_subjects()[0].get_element() is not inner
    assert copied_note.get_subjects()[1].get_element() is outer
    del copied_note
    del copied
    gc.collect()

    # a subject that targets the moved subtree root must re-bind to the copy:
    # copy + rebind + remove the original + add the copy
    sm1 = d1.get_state_machines()[0]
    rootnote = d1.new_comment(sm1, "points at the composite")
    d1.add_comment_to_element(rootnote, composite)
    cparent = composite.get_parent()
    composite_id = composite.get_id()
    moved = composite.copy(cparent)
    d1.rebind_subjects(moved)
    assert rootnote.get_subjects()[-1].get_element() is moved
    assert rootnote.get_subjects()[-1].get_element() is not composite
    del composite, inner, nested
    cparent.remove_element(composite_id)
    cparent.add_element(moved)
    rebound = d1.encode()
    assert rebound

    # the collection owns the added copy: dropping the python handle keeps it
    assert moved.get_parent() is cparent
    del moved
    gc.collect()
    assert d1.find_element_by_id(composite_id) is not None
    assert rootnote.get_subjects()[-1].get_element().get_id() == composite_id
    assert d1.encode() == rebound

    # the same for an element constructed in python
    pynote = CyberiadaML.Comment(sm1, "py-note", "A python note")
    sm1.add_element(pynote)
    del pynote
    gc.collect()
    assert sm1.find_element_by_id("py-note").get_body() == "A python note"
    assert d1.encode()

    # a refused add keeps the python ownership
    orphan = outer.copy(None)
    refused = False
    try:
        sm1.add_element(orphan)
    except CyberiadaML.AssertException:
        refused = True
    assert refused
    del orphan
    gc.collect()

    del outer, rootnote, cparent, sm1
    del d1, ld2, e3
    gc.collect()
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
