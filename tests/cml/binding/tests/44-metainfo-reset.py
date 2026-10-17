#!/usr/bin/python3
# -----------------------------------------------------------------------------
#  The Python binding for Cyberiada GraphML library
# 
#  The metainformation and document reset test
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
    ld.open(sys.argv[0] + "-input.graphml", CyberiadaML.formatCyberiada10)

    # the metainformation strings
    assert ld.meta().get_string("platform") == "Berloga"
    assert ld.meta().get_string("nonexistent") == ""
    ld.meta().set_string("platform", "Arduino")
    assert ld.meta().get_string("platform") == "Arduino"
    ld.meta().set_string("customKey", "custom value")
    assert ld.meta().get_string("customKey") == "custom value"

    # the document rename updates the meta comment
    ld.set_name("Updated document")
    assert ld.meta().get_string("name") == "Updated document"
    assert ld.get_meta_element() is not None

    # the metainfo comment update is a stub
    assert not ld.update_metainfo_from_comment("name/ Other")

    # the encode/decode buffer round trip
    buffer = ld.encode(CyberiadaML.formatCyberiada10)
    d2 = CyberiadaML.Document()
    (format, format_str) = d2.decode(buffer)
    assert format == CyberiadaML.formatCyberiada10
    assert d2.elements_count() == ld.elements_count()
    assert d2.meta().get_string("customKey") == "custom value"

    print(d2)

    # opening without geometry
    ld2 = CyberiadaML.LocalDocument()
    ld2.open(sys.argv[0] + "-input.graphml", CyberiadaML.formatCyberiada10,
             CyberiadaML.geometryFormatNone)
    assert ld2.get_geometry_format() == CyberiadaML.geometryFormatNone
    assert not ld2.has_geometry()

    # renaming an empty document
    empty = CyberiadaML.Document()
    empty.set_name("No SM")
    assert empty.get_name() == "No SM"
    assert empty.get_meta_element() is None

    # the document reset
    ld.reset()
    assert ld.children_count() == 0
    assert ld.get_file_path() == ""
    assert ld.get_file_format() == CyberiadaML.formatCyberiada10
except Exception as e:
    sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
    sys.stderr.write('{}\n'.format(traceback.format_exc()))
    exit(1)

exit(0)
