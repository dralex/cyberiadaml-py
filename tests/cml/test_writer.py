# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The building and writing of the CyberiadaML interface
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
"""Building documents with cml: factories, checks, encode and save."""
import pytest
from cyberiadaml_py import cml, core

STATES = (cml.elementSimpleState, cml.elementCompositeState)


def _machine():
    doc = cml.Document()
    return doc, doc.new_state_machine('SM')


def _reread(doc):
    """Return the document read back from its text (strictly)."""
    text = doc.encode()
    core.read(text, strict=True)
    copy = cml.Document()
    copy.decode(text, cml.formatCyberiada10, cml.geometryFormatNone,
                strict=True)
    return copy


def test_generated_ids():
    """Check the factories number the elements as the binding does."""
    doc, sm = _machine()
    assert sm.get_id() == 'G0'
    assert doc.new_state_machine('SM 2').get_id() == 'G1'
    a = doc.new_state(sm, 'A')
    b = doc.new_state(sm, 'B')
    inner = doc.new_state(a, 'Inner')
    assert (a.get_id(), b.get_id(), inner.get_id()) == ('n0', 'n1', 'n0::n0')
    assert doc.new_initial(sm).get_id() == 'n2'
    first = doc.new_transition(sm, cml.transitionExternal, a, b,
                               cml.Action('GO'))
    second = doc.new_transition(sm, cml.transitionExternal, a, b,
                                cml.Action('AGAIN'))
    assert (first.get_id(), second.get_id()) == ('n0-n1', 'n0-n1#0')
    note = doc.new_comment(sm, 'A note')
    subjects = [doc.add_comment_to_element(note, a),
                doc.add_comment_to_element_name(note, a, 'A'),
                doc.add_comment_to_element_body(note, b, 'GO')]
    assert [s.get_id() for s in subjects] == [
        'n3-n0', 'n3-n0#0', 'n3-n1']
    # a subject is returned as a copy
    assert subjects[0] is not note.get_subjects()[0]


def test_overloads():
    """Check the string arguments select the binding's overloads."""
    doc, sm = _machine()
    state = doc.new_state(sm, 'idle', 'Idle', cml.Action('TICK', '', 'f()'))
    assert (state.get_id(), state.get_name()) == ('idle', 'Idle')
    assert state.get_actions()[0].get_trigger() == 'TICK'
    initial = doc.new_initial(sm, 'start')
    assert (initial.get_id(), initial.get_name()) == ('n0', 'start')
    final = doc.new_final(sm, 'fin', 'End')
    assert (final.get_id(), final.get_name()) == ('fin', 'End')
    sub = doc.new_submachine_state(sm, 'G1', 'Sub')
    assert (sub.get_submachine_reference(), sub.get_name()) == ('G1', 'Sub')
    entry = doc.new_entry(sub, 'in')
    assert (entry.get_id(), entry.get_name()) == (sub.get_id() + '::n0',
                                                  'in')
    named = doc.new_formal_comment(sm, 'CGML_COMPONENT timer', 'type/ Timer')
    assert named.get_name() == 'CGML_COMPONENT timer'
    assert named.get_type() == cml.elementFormalComment


@pytest.mark.parametrize('call, message', [
    (lambda d, sm, s: d.new_state(None, 'A'), 'No parent element'),
    (lambda d, sm, s: d.new_state(sm, ''), 'Empty string parameter'),
    (lambda d, sm, s: d.new_state(sm, 'n0', 'B'), 'is not unique'),
    (lambda d, sm, s: (d.new_initial(sm), d.new_initial(sm)),
     'already has initial'),
    (lambda d, sm, s: (d.new_deep_history(s), d.new_deep_history(s)),
     'deep history'),
    (lambda d, sm, s: d.new_transition(
        sm, cml.transitionExternal, d.new_final(sm), s, cml.Action('E')),
     'Bad source'),
    (lambda d, sm, s: d.new_transition(
        sm, cml.transitionExternal, s, d.new_initial(sm), cml.Action('E')),
     'Bad target'),
    (lambda d, sm, s: d.new_transition(
        sm, cml.transitionExternal, s, s, cml.Action(cml.actionEntry, 'f')),
     'entry/exit'),
    (lambda d, sm, s: d.add_comment_to_element(d.new_comment(sm, 'x'), sm),
     'Bad element to comment'),
])
def test_factory_checks(call, message):
    """Check the factories refuse what the C++ library refuses."""
    doc, sm = _machine()
    state = doc.new_state(sm, 'A')
    with pytest.raises(cml.ParametersException, match=message):
        call(doc, sm, state)


def test_choice_single_incoming():
    """Check a choice takes one incoming transition."""
    doc, sm = _machine()
    a, b = doc.new_state(sm, 'A'), doc.new_state(sm, 'B')
    choice = doc.new_choice(sm)
    doc.new_transition(sm, cml.transitionExternal, a, choice, cml.Action('E'))
    with pytest.raises(cml.ParametersException, match='only one incoming'):
        doc.new_transition(sm, cml.transitionExternal, b, choice,
                           cml.Action('F'))


def test_geometry_switches_format():
    """Check a geometry given to a factory makes the document Qt."""
    doc, sm = _machine()
    doc.new_state(sm, 'A')
    assert doc.get_geometry_format() == cml.geometryFormatNone
    doc.new_state(sm, 'B', cml.Action(), cml.Rect(0, 0, 10, 10))
    assert doc.get_geometry_format() == cml.geometryFormatQt
    with pytest.raises(cml.NotImplementedException):
        doc.encode()
    assert 'dGeometry' not in doc.encode(skip_geometry=True)


def test_round_trip():
    """Check every kind of element comes back from its text."""
    doc, sm = _machine()
    doc.set_name('All kinds')
    doc.get_meta().set_string('platform', 'Test')
    initial = doc.new_initial(sm)
    state = doc.new_state(sm, 'Composite', cml.Action(cml.actionEntry, 'on()'))
    state.add_action(cml.Action('TICK', 'n > 0', 'count();',
                                cml.eventPropagationBlock))
    inner = doc.new_state(state, 'Inner')
    doc.new_shallow_history(state)
    doc.new_deep_history(state)
    choice = doc.new_choice(sm)
    final = doc.new_final(sm)
    terminate = doc.new_terminate(sm)
    sub = doc.new_submachine_state(sm, 'G1', 'Sub')
    entry, leave = doc.new_entry(sub, 'in'), doc.new_exit(sub, 'out')
    other = doc.new_state_machine('Other')
    doc.new_initial(other)
    # the points of a submachine state are those of its machine (8.3)
    doc.new_entry(other, 'in')
    doc.new_exit(other, 'out')
    note = doc.new_comment(sm, 'Note', 'A note', cml.Rect(), '', 'markdown')
    doc.add_comment_to_element(note, inner)
    doc.add_comment_to_element_body(note, state, 'count')
    for source, target, action in (
            (initial, state, cml.Action()),
            (inner, choice, cml.Action('GO')),
            (choice, final, cml.Action('', 'ok', '')),
            (choice, sub, cml.Action('', 'else', '')),
            (leave, terminate, cml.Action('DONE', '', 'stop();',
                                          cml.eventPropagationPropagate))):
        doc.new_transition(sm, cml.transitionExternal, source, target,
                           action)
    assert entry.get_parent() is sub
    copy = _reread(doc)
    # the read document has its CGML_META comment
    copy.get_state_machines()[0].remove_element('nMeta')
    assert repr(copy).replace('type: loc', 'type: ext') == \
        repr(doc).replace('type: loc', 'type: ext')
    assert copy.get_meta().get_string('name') == 'All kinds'


def test_meta_element():
    """Check the CGML_META comment follows the metainformation."""
    doc = cml.LocalDocument()
    doc.decode(_minimal())
    meta = doc.get_meta_element()
    assert meta is not None
    doc.set_name('Renamed')
    assert 'name/ Renamed' in meta.get_body()
    assert doc.update_metainfo_from_comment('name/ X') is False


def _minimal() -> str:
    doc, sm = _machine()
    doc.new_state(sm, 'A')
    return doc.encode()


def test_encode_options():
    """Check the format and the options of encode."""
    doc, sm = _machine()
    doc.new_state(sm, 'A')
    with pytest.raises(cml.ParametersException, match='Bad save format'):
        doc.encode(cml.formatDetect)
    with pytest.raises(cml.NotImplementedException):
        doc.encode(cml.formatLapki)
    with pytest.raises(TypeError):
        doc.encode('')
    with pytest.raises(cml.ParametersException):
        cml.Document().encode()
    # the options need the geometry, as in the C++ library
    assert doc.encode(check_initial=True)
    geometry = cml.Document(cml.geometryFormatCyberiada10)
    gsm = geometry.new_state_machine('SM')
    geometry.new_state(gsm, 'A', cml.Action(), cml.Rect(0.12345, 0, 10, 10))
    assert '0.1235' in geometry.encode(round=True)
    with pytest.raises(cml.CybMLException, match='single initial'):
        geometry.encode(check_initial=True)
    state = geometry.find_element_by_id('n0')
    state.add_action(cml.Action(cml.actionEntry, 'a()'))
    state.add_action(cml.Action(cml.actionEntry, 'b()'))
    with pytest.raises(cml.CybMLException, match='Multiple entry'):
        geometry.encode(strict_actions=True)


def test_defer_with_behaviour_refused():
    """Check a deferred event with behaviour is not written (6.8)."""
    doc, sm = _machine()
    state = doc.new_state(sm, 'A')
    state.add_action(cml.Action('TICK', '', '', cml.eventPropagationDefer))
    assert 'TICK/ defer' in doc.encode()
    state.add_action(cml.Action('TOCK', '', 'f();', cml.eventPropagationDefer))
    with pytest.raises(cml.CybMLException, match='defer'):
        doc.encode()


def test_reading_legacy_forms():
    """Check the forms the binding reads besides the standard ones."""
    doc, sm = _machine()
    state = doc.new_state(sm, 'A')
    state.add_action(cml.Action('TICK', '', 'f();'))
    text = doc.encode().replace('TICK/', 'TICK defer/')
    text = text.replace('<data key="dName">SM</data>',
                        '<data key="dName">SM</data>\n'
                        '    <data key="referenceGraphID">arena</data>')
    read = cml.Document()
    assert read.decode(text, cml.formatDetect, cml.geometryFormatNone) == (
        cml.formatCyberiada10, 'Cyberiada-GraphML-Arena')
    action = read.find_element_by_id('n0').get_actions()[0]
    assert action.get_trigger() == 'TICK'
    assert action.get_propagation() == cml.eventPropagationDefer


def test_copies_are_independent():
    """Check the copy constructors copy the tree."""
    doc, sm = _machine()
    state = doc.new_state(sm, 'A')
    copy = cml.Document(doc)
    state.set_name('Changed')
    assert copy.find_element_by_id('n0').get_name() == 'A'
    assert copy.get_state_machines()[0].get_parent() is copy
    local = cml.LocalDocument(doc, 'a.graphml', cml.formatCyberiada10)
    assert local.get_file_path() == 'a.graphml'
    again = cml.LocalDocument(local)
    assert again.get_file_path() == 'a.graphml'
    assert cml.StateMachine(sm).get_id() == sm.get_id()
    doc.reset()
    assert not doc.get_children()
    assert doc.get_meta().transition_order == cml.transitionOrderAction


def test_save(tmp_path):
    """Check save, save_as and the file errors."""
    doc, sm = _machine()
    doc.new_state(sm, 'A')
    local = cml.LocalDocument(doc, str(tmp_path / 'a.graphml'))
    local.save()
    path = str(tmp_path / 'b.graphml')
    local.save_as(path)
    assert local.get_file_path() == path
    read = cml.LocalDocument()
    read.open(path)
    assert [repr(s) for s in read.find_elements_by_types(STATES)] == [
        repr(s) for s in doc.find_elements_by_types(STATES)]
    with pytest.raises(cml.FileException, match='Cannot open file'):
        local.save_as(str(tmp_path / 'missing' / 'c.graphml'))
    assert local.get_file_path() == path
