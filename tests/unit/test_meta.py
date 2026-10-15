# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The 6.9 metadata parameter parser tests
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------
"""The 6.9 metadata parameter parser tests."""
from cyberiadaml_py.core.meta import parse


def pairs(params):
    """Return pairs."""
    return [(p.name, p.value) for p in params]


def test_empty_text():
    """Check empty text."""
    for text in (None, '', '\n\n'):
        params, errors = parse(text)
        assert params == []
        assert errors == []


def test_single_parameter():
    """Check single parameter."""
    params, errors = parse('standardVersion/ 1.0')
    assert errors == []
    assert pairs(params) == [('standardVersion', '1.0')]


def test_multiple_parameters_ordered():
    """Check multiple parameters ordered."""
    text = 'standardVersion/ 1.0\n\ngeometry/ short\n\nauthor/ A. Author'
    params, errors = parse(text)
    assert errors == []
    assert pairs(params) == [('standardVersion', '1.0'),
                             ('geometry', 'short'),
                             ('author', 'A. Author')]


def test_multiline_value():
    """Check multiline value."""
    text = 'description/ first line\nsecond line\nthird line'
    params, errors = parse(text)
    assert errors == []
    assert pairs(params) == [
        ('description', 'first line\nsecond line\nthird line')]


def test_no_space_after_slash():
    """Check no space after slash."""
    params, _ = parse('name/value')
    assert pairs(params) == [('name', 'value')]


def test_whitespace_around_the_slash_is_trimmed():
    """Check whitespace around the slash is trimmed."""
    params, _ = parse('name \t/ \t double space ')
    assert pairs(params) == [('name', 'double space ')]


def test_missing_slash_is_an_error():
    """Check missing slash is an error."""
    params, errors = parse('standardVersion 1.0')
    assert params == []
    assert len(errors) == 1
    assert "missing '/'" in errors[0][1]


def test_empty_name_is_an_error():
    """Check empty name is an error."""
    params, errors = parse('/ value')
    assert params == []
    assert len(errors) == 1
    assert 'empty parameter name' in errors[0][1]


def test_non_latin_name_parsed_for_l3():
    """Check non latin name parsed for L3."""
    # the parser keeps the name; the charset is judged by the L3 checks
    params, errors = parse('имя/ значение')
    assert errors == []
    assert pairs(params) == [('имя', 'значение')]


def test_component_body_grammar():
    """Check component body grammar."""
    text = 'id/ c1\n\ntype/ LED\n\nname/ Front light'
    params, errors = parse(text)
    assert errors == []
    assert pairs(params) == [('id', 'c1'), ('type', 'LED'),
                             ('name', 'Front light')]


def test_error_line_numbers():
    """Check error line numbers."""
    _, errors = parse('a/ 1\n\nbroken\n\nb/ 2')
    assert errors == [(2, "missing '/' in the parameter description")]
