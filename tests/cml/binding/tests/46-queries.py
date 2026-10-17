#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The collection queries test
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
    assert not sm.has_initial()

    # augment the hierarchy with an initial, a transition and a comment
    p0 = sm.find_element_by_id("n0")
    assert p0 is not None
    init = ld.new_initial(sm)
    ld.new_transition(sm, CyberiadaML.transitionExternal, init, p0, CyberiadaML.Action())
    ld.new_comment(sm, "A comment")
    assert sm.has_initial()

    # the element access by index
    print("children: {}".format(sm.children_count()))
    print("elements: {}".format(ld.elements_count()))
    first = sm.first_element()
    assert first.get_id() == sm.get_element(0).get_id()
    assert sm.get_element(sm.children_count()) is None
    assert sm.element_index(first) == 0
    assert first.index() == 0
    print("first: {}".format(first.get_id()))
    last = sm.get_element(sm.children_count() - 1)
    assert last.index() == sm.children_count() - 1
    print("last: {}".format(last.get_id()))

    # the children list
    assert len(sm.get_children()) == sm.children_count()

    # the deep search by identifier
    deep = ld.find_element_by_id("n0::n1::n0")
    assert deep is not None
    print("deep: {}".format(deep.get_qualified_name()))
    assert deep.has_qualified_name()
    assert ld.find_element_by_id("nonexistent") is None
    deep2 = ld.find_element_by_id("n0::n1::n1")
    assert deep2 is not None
    print("deep2: {}".format(deep2.get_qualified_name()))

    # the vertexes
    vertexes = sm.get_vertexes()
    print("vertexes: {}".format(len(vertexes)))

    # the substates
    substates = p0.get_substates()
    print("substates:" + "".join([" '{}'".format(s.get_name()) for s in substates]))

    # the comments and transitions
    print("comments: {} transitions: {}".format(len(sm.get_comments()), len(sm.get_transitions())))
    print("const comments: {} const transitions: {}".format(len(sm.get_comments()),
                                                            len(sm.get_transitions())))

    # the parent state machine
    assert ld.get_parent_sm(deep).get_id() == sm.get_id()
    assert ld.get_parent_sm(sm).get_id() == sm.get_id()
    assert ld.get_parent_sm(ld) is None
    assert ld.get_parent_sm(None) is None
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
