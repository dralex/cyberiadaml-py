#!/usr/bin/env python3
#  -----------------------------------------------------------------------------
#  The Cyberiada State Machine Editor
#  The Python bindings for the C++ library for CyberiadaML files
#
#  The bound rect with and without the comments
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

# a comment far outside the states widens the plain bound rect only; the
# overload excluding the comments keeps the rect of the states (the SM border
# fit of the library, ElementCollection::get_bound_rect(d, exclude_comments))
try:
    d = CyberiadaML.Document()
    sm = d.new_state_machine("SM")
    d.new_state(sm, "A", CyberiadaML.Action(), CyberiadaML.Rect(0, 0, 100, 50))
    d.new_state(sm, "B", CyberiadaML.Action(), CyberiadaML.Rect(200, 0, 100, 50))
    d.new_comment(sm, "far away", CyberiadaML.Rect(1000, 1000, 100, 30))

    with_comments = sm.get_bound_rect(d)
    without = sm.get_bound_rect(d, True)
    assert with_comments.width > without.width, (with_comments, without)
    assert with_comments.height > without.height, (with_comments, without)
    assert sm.get_bound_rect(d, False).width == with_comments.width
    assert without.width <= 300 and without.height <= 50, without
except Exception as e:
    print(traceback.format_exc())
    sys.exit(1)
sys.exit(0)
