#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
#
#  The comment subjects test: the geometry, the target, the type and the
#  fragment changed in place
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


def refused(call):
    try:
        call()
    except CyberiadaML.ParametersException:
        return True
    return False


try:
    d = CyberiadaML.Document(CyberiadaML.geometryFormatQt)
    sm = d.new_state_machine("sm1", "SM", CyberiadaML.Rect(0, 0, 600, 400))
    s1 = d.new_state(sm, "s1", "State 1", CyberiadaML.Action(), CyberiadaML.Rect(-150, -100, 100, 50))
    s2 = d.new_state(sm, "s2", "State 2", CyberiadaML.Action(CyberiadaML.actionEntry, "init();"),
                     CyberiadaML.Rect(150, -100, 100, 50))
    t = d.new_transition(sm, CyberiadaML.transitionExternal, s1, s2, CyberiadaML.Action("GO"))
    c = d.new_comment(sm, "A note", CyberiadaML.Rect(0, 100, 100, 40))
    d.add_comment_to_element(c, s1, CyberiadaML.Point(-50, 0), CyberiadaML.Point(0, 25))
    d.add_comment_to_element(c, t, CyberiadaML.Point(0, -20), CyberiadaML.Point(150, 0))

    pl = CyberiadaML.Polyline()
    pl.append(CyberiadaML.Point(-20, -60))
    c.update_subject_geometry(0, CyberiadaML.Point(-50, -20), CyberiadaML.Point(25, 25), pl)
    print("geometry:", c.get_subjects()[0])

    s = d.update_comment_subject(c, 0, s2)
    print("retarget:", s)
    print("order kept:", c.get_subjects()[1].get_element().get_id())

    d.update_comment_subject(c, 0, s2, CyberiadaML.commentSubjectData, "init")
    c.update_subject_geometry(0, CyberiadaML.Point(-50, 0), CyberiadaML.Point(10, 10))
    print("fragment:", c.get_subjects()[0])

    c.update_subject(1, CyberiadaML.CommentSubject("link", t, CyberiadaML.Point(0, -20)))
    print("replaced:", c.get_subjects()[1])

    print("refused the machine:", refused(lambda: d.update_comment_subject(c, 0, sm)))
    print("refused the comment itself:", refused(lambda: d.update_comment_subject(c, 0, c)))
    print("refused a bad index:", refused(lambda: d.update_comment_subject(c, 2, s1)))
    print("refused an empty fragment:",
          refused(lambda: d.update_comment_subject(c, 0, s1, CyberiadaML.commentSubjectName, "")))
    print("refused a bad geometry index:",
          refused(lambda: c.update_subject_geometry(5, CyberiadaML.Point(0, 0))))
except CyberiadaML.Exception as e:
    print("error:", e)
    traceback.print_exc()
    sys.exit(1)
