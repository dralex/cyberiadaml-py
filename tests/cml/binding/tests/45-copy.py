#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The elements copy test
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
    ld = CyberiadaML.LocalDocument()
    ld.open(sys.argv[0] + "-input.graphml")
    sm = ld.get_state_machines()[0]

    # augment the diagram so every element kind is copied
    state = sm.find_elements_by_type(CyberiadaML.elementSimpleState)[0]
    ld.new_final(sm)
    ld.new_terminate(sm)
    ld.new_choice(sm)
    comment = ld.new_comment(sm, "A comment")
    ld.add_comment_to_element(comment, state)
    ld.add_comment_to_element_name(comment, state, state.get_name())

    # the document copy constructor copies every element
    d1 = CyberiadaML.Document(ld)
    d2 = CyberiadaML.Document(d1)
    assert repr(d2) == repr(d1)
    assert d2.elements_count() == d1.elements_count()
    sm1 = d1.get_state_machines()[0]
    sm2 = d2.get_state_machines()[0]
    assert sm1.check_isomorphism(sm2, False) == CyberiadaML.smiIdentical

    # the local document copies
    ld2 = CyberiadaML.LocalDocument(ld)
    assert repr(ld2) == repr(ld)
    assert ld2.get_file_path() == ld.get_file_path()
    ldc = ld.copy(None)
    assert repr(ldc) == repr(ld)

    # the individual element copies
    smc = sm1.copy(None)
    assert smc.get_id() == sm1.get_id()
    assert smc.elements_count() == sm1.elements_count()

    st = d1.find_elements_by_type(CyberiadaML.elementSimpleState)[0]
    stc = st.copy(st.get_parent())
    assert stc.get_id() == st.get_id()
    assert repr(stc) == repr(st)

    tr = d1.get_state_machines()[0].get_transitions()[0]
    trc = tr.copy(tr.get_parent())
    assert trc.get_id() == tr.get_id()
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
