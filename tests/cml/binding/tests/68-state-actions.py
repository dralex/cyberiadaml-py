#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
#
#  The state actions test: set, clear and remove the actions of a state
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


def show(state):
    actions = state.get_actions()
    print("actions:", len(actions))
    for a in actions:
        print("  ", a)


try:
    d = CyberiadaML.Document()
    sm = d.new_state_machine("SM")
    init = d.new_initial(sm)
    s = d.new_state(sm, "S")
    d.new_transition(sm, CyberiadaML.transitionExternal, init, s, CyberiadaML.Action())
    s.add_action(CyberiadaML.Action(CyberiadaML.actionEntry, "old()"))

    # a plain list is taken as well as the list of get_actions()
    actions = [CyberiadaML.Action(CyberiadaML.actionEntry, "start()"),
               CyberiadaML.Action("KEY", "ready", "pressed()",
                                  CyberiadaML.eventPropagationPropagate),
               CyberiadaML.Action("LATER", "", "", CyberiadaML.eventPropagationDefer),
               CyberiadaML.Action(CyberiadaML.actionExit, "stop()")]
    s.set_actions(actions)
    print("set")
    show(s)
    s.set_actions(s.get_actions())
    print("set from get_actions:", len(s.get_actions()))

    try:
        s.set_actions(actions + [CyberiadaML.Action()])
        print("the empty transition action accepted")
    except CyberiadaML.ParametersException:
        print("the empty transition action refused")
    print("unchanged:", len(s.get_actions()))
    try:
        s.set_actions(["not an action"])
        print("a string accepted")
    except RuntimeError:
        print("a string refused")

    s.remove_action(1)
    print("removed 1")
    show(s)
    try:
        s.remove_action(9)
        print("index 9 accepted")
    except CyberiadaML.ParametersException:
        print("index 9 refused")

    text = d.encode()
    copy = CyberiadaML.Document()
    copy.decode(text, strict=True)
    print("strict round trip:", s.compare_actions(copy.find_element_by_id(s.get_id())))

    s.clear_actions()
    print("cleared:", int(s.has_actions()))
except Exception:
    traceback.print_exc()
    sys.exit(1)
