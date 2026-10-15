# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The 6.8 behaviour text parser tests
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
"""The 6.8 behaviour text parser tests."""
from cyberiadaml_py.core.actions import parse

MISSING_SEPARATOR = "missing '/' before the behaviour lines"


def test_empty_value_is_zero_blocks():
    """Check empty value is zero blocks."""
    for text in (None, '', '\n', '  \n  '):
        blocks, errors = parse(text)
        assert blocks == []
        assert errors == []


def test_entry_block_with_body():
    """Check entry block with body."""
    blocks, errors = parse('entry/\nLED.on();')
    assert errors == []
    assert len(blocks) == 1
    assert blocks[0].kind == 'entry'
    assert blocks[0].behaviour == ['LED.on();']


def test_inline_behaviour_after_keyword():
    """Check inline behaviour after keyword."""
    blocks, _ = parse('exit/ LED.off();')
    assert blocks[0].kind == 'exit'
    assert blocks[0].behaviour == ['LED.off();']


def test_keyword_with_empty_body():
    """Check keyword with empty body."""
    for text in ('entry/', 'exit/', 'do/'):
        blocks, errors = parse(text)
        assert errors == []
        assert blocks[0].kind == text[:-1]
        assert blocks[0].behaviour == []


def test_multiple_blocks_order_preserved():
    """Check multiple blocks order preserved."""
    text = 'entry/\na();\n\nTIMER/\nb();\n\nexit/\nc();'
    blocks, errors = parse(text)
    assert errors == []
    assert [b.kind for b in blocks] == ['entry', 'event', 'exit']
    assert blocks[1].trigger == 'TIMER'
    assert blocks[1].behaviour == ['b();']


def test_consecutive_blank_lines_make_no_empty_blocks():
    """Check consecutive blank lines make no empty blocks."""
    blocks, _ = parse('entry/\n\n\n\nexit/')
    assert [b.kind for b in blocks] == ['entry', 'exit']


def test_trigger_with_guard_and_behaviour():
    """Check trigger with guard and behaviour."""
    blocks, errors = parse('TIMER(100) [cnt > 0]/ blink()')
    assert errors == []
    block = blocks[0]
    assert block.kind == 'event'
    assert block.trigger == 'TIMER(100)'
    assert block.guard == 'cnt > 0'
    assert block.behaviour == ['blink()']


def test_trigger_with_guard_and_empty_behaviour():
    """Check trigger with guard and empty behaviour."""
    blocks, errors = parse('EVENT [x = 1]/')
    assert errors == []
    assert blocks[0].trigger == 'EVENT'
    assert blocks[0].guard == 'x = 1'
    assert blocks[0].behaviour == []


def test_event_parameters():
    """Check event parameters."""
    for param in ('propagate', 'block'):
        blocks, errors = parse('TIMER %s/ x()' % param)
        assert errors == []
        assert blocks[0].trigger == 'TIMER'
        assert blocks[0].param == param
    blocks, errors = parse('TIMER/ defer')
    assert errors == []
    assert (blocks[0].trigger, blocks[0].param) == ('TIMER', 'defer')


def test_parameter_with_guard():
    """Check parameter with guard."""
    blocks, _ = parse('TIMER [cnt > 0] propagate/ x()')
    assert blocks[0].trigger == 'TIMER'
    assert blocks[0].param == 'propagate'
    assert blocks[0].guard == 'cnt > 0'


def test_else_guard():
    """Check else guard."""
    blocks, errors = parse('[else]/ fallback()')
    assert errors == []
    assert blocks[0].trigger == ''
    assert blocks[0].guard == 'else'
    assert blocks[0].behaviour == ['fallback()']


def test_escaped_brackets_in_guard():
    """Check escaped brackets in guard."""
    blocks, errors = parse('E [Строка.Содержит(\\[Пример\\])]/')
    assert errors == []
    assert blocks[0].guard == 'Строка.Содержит([Пример])'


def test_exotic_event_names_preserved():
    """Check exotic event names preserved."""
    for trigger in ('Module.Event', 'EVENT(a, b)', 'Событие'):
        blocks, errors = parse(trigger + '/')
        assert errors == []
        assert blocks[0].trigger == trigger


def test_slash_inside_arguments_not_a_separator():
    """Check slash inside arguments not a separator."""
    blocks, _ = parse('E(a/b)/ x()')
    assert blocks[0].trigger == 'E(a/b)'
    assert blocks[0].behaviour == ['x()']


def test_multiline_behaviour_preserved():
    """Check multiline behaviour preserved."""
    text = 'TIMER/\nfirst();\n  indented();\nlast();'
    blocks, _ = parse(text)
    assert blocks[0].behaviour == ['first();', '  indented();', 'last();']
    assert blocks[0].verbatim == text


def test_event_without_separator():
    """Check event without separator."""
    blocks, errors = parse('EV', transition=True)
    assert errors == []
    assert blocks[0].kind == 'event'
    assert blocks[0].trigger == 'EV'
    assert blocks[0].guard is None
    assert blocks[0].behaviour == []


def test_event_with_guard_without_separator():
    """Check event with guard without separator."""
    blocks, errors = parse('EV [x > 1]', transition=True)
    assert errors == []
    assert blocks[0].trigger == 'EV'
    assert blocks[0].guard == 'x > 1'
    assert blocks[0].behaviour == []


def test_multiline_header_standard_example():
    """Check multiline header standard example."""
    text = 'Сенсор.ЦельПолучена\n[Счетчик.ТекущееЗначениеСчетчика >= 2]'
    blocks, errors = parse(text, transition=True)
    assert errors == []
    assert blocks[0].trigger == 'Сенсор.ЦельПолучена'
    assert blocks[0].guard == 'Счетчик.ТекущееЗначениеСчетчика >= 2'
    assert blocks[0].behaviour == []
    assert blocks[0].verbatim == text


def test_separator_on_second_line():
    """Check separator on second line."""
    blocks, errors = parse('EV\n[g]/ act()\nmore()', transition=True)
    assert errors == []
    assert blocks[0].trigger == 'EV'
    assert blocks[0].guard == 'g'
    assert blocks[0].behaviour == ['act()', 'more()']


def test_event_parameter_after_guard():
    """Check event parameter after guard."""
    blocks, errors = parse('STOP [ready] block/ halt()')
    assert errors == []
    assert (blocks[0].trigger, blocks[0].param, blocks[0].guard) == \
        ('STOP', 'block', 'ready')


def test_keyword_before_guard_stays_in_the_event_name():
    """Check keyword before guard stays in the event name."""
    blocks, errors = parse('START propagate [g]/')
    assert errors == []
    assert (blocks[0].trigger, blocks[0].param, blocks[0].guard) == \
        ('START propagate', None, 'g')


def test_pre_separator_parameter_without_guard():
    """Check pre separator parameter without guard."""
    blocks, errors = parse('START propagate/')
    assert errors == []
    assert (blocks[0].trigger, blocks[0].param) == ('START', 'propagate')


def test_defer_after_separator():
    """Check defer after separator."""
    blocks, errors = parse('TICK/ defer')
    assert errors == []
    assert (blocks[0].trigger, blocks[0].param) == ('TICK', 'defer')
    assert blocks[0].behaviour == []
    blocks, errors = parse('TICK [g]/ defer\nact()')
    assert (blocks[0].param, blocks[0].guard) == ('defer', 'g')
    assert [e[2] for e in errors] == ['defer-usage']
    blocks, errors = parse('TICK/ defer', transition=True)
    assert [e[2] for e in errors] == ['defer-usage']
    blocks, _ = parse('TICK/ deferred()')
    assert blocks[0].param is None
    assert blocks[0].behaviour == ['deferred()']


def test_defer_before_separator_stays_in_the_event_name():
    """Check defer before separator stays in the event name."""
    blocks, errors = parse('TICK defer/')
    assert errors == []
    assert (blocks[0].trigger, blocks[0].param) == ('TICK defer', None)


def test_empty_event_name_in_node_is_accepted():
    """Check empty event name in node is accepted."""
    blocks, errors = parse('/ x()')
    assert errors == []
    assert blocks[0].trigger == ''
    assert blocks[0].behaviour == ['x()']


def test_completion_transition():
    """Check completion transition."""
    for text in ('/ finish()', '/', '[done]/ finish()'):
        blocks, errors = parse(text, transition=True)
        assert errors == [], text
        assert blocks[0].kind == 'event'
        assert blocks[0].trigger == ''
    assert blocks[0].guard == 'done'
    assert blocks[0].behaviour == ['finish()']


def test_node_event_without_behaviour_accepted():
    """Check node event without behaviour accepted."""
    blocks, errors = parse('EV')
    assert errors == []
    assert blocks[0].trigger == 'EV'
    assert blocks[0].behaviour == []


def test_node_behaviour_lines_require_separator():
    """Check node behaviour lines require separator."""
    blocks, errors = parse('EV\n[g]')
    assert errors == [(0, MISSING_SEPARATOR, 'behaviour-syntax')]
    assert blocks[0].trigger == 'EV'
    assert blocks[0].behaviour == ['[g]']


def test_error_line_numbers():
    """Check error line numbers."""
    _, errors = parse('entry/\na()\n\nbroken\nlines')
    assert errors == [(3, MISSING_SEPARATOR, 'behaviour-syntax')]
    _, errors = parse('entry/\na()\n\n/ x()')
    assert errors == []


def test_reserved_event_names_and_empty_event_params():
    """Check reserved event names and empty event params."""
    for name in ('entry', 'exit', 'do', 'defer', 'else'):
        _, errors = parse('%s/ x()' % name, transition=True)
        assert [e[2] for e in errors] == ['event-name-reserved'], name
    _, errors = parse('ANY/ x()\n\nUNKNOWN/ y()')
    assert errors == []
    _, errors = parse('propagate/ x()', transition=True)
    assert [e[2] for e in errors] == ['param-needs-event']
    _, errors = parse('[g] block/', transition=True)
    assert [e[2] for e in errors] == ['param-needs-event']
    _, errors = parse('entry/ a()\n\nexit/ b()\n\nentry/ c()')
    assert [e[2] for e in errors] == ['behaviour-block-once']
