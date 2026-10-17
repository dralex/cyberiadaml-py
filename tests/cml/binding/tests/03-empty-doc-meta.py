#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The empty document metainformation test
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

try:
    d = CyberiadaML.LocalDocument()
    d.new_state_machine("SM", CyberiadaML.Rect())
    d.get_meta().set_string("platform", "Berloga")
    d.get_meta().set_string("platformVersion", "1.4")
    d.get_meta().set_string("platformLanguage", "script")
    d.get_meta().set_string("target", "Unit")
    d.get_meta().set_string("name", "Test document")
    d.get_meta().set_string("author", "Author")
    d.get_meta().set_string("contact", "platform@kruzhok.org")
    d.get_meta().set_string("description", "1\n2\n3") 
    d.get_meta().set_string("version", "0.1")
    d.get_meta().set_string("date", "2024-04-14T11:22:00")
    d.get_meta().set_string("markupLanguage", "html")
    d.get_meta().transition_order = CyberiadaML.transitionOrderExit
    d.get_meta().event_propagation = CyberiadaML.docEventPropagationPropagate
    d.save_as(sys.argv[0] + ".graphml", CyberiadaML.formatCyberiada10, False)
except Exception as e:
    print('Unexpected exception: {}'.format(e.__class__))
    print(traceback.format_exc())
    exit(1)

exit(0)
