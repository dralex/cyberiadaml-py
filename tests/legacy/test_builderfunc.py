"""Tests for CGMLBuilder with both function and state machine."""
import xml.etree.ElementTree as ET

import pytest
from cyberiadaml_py.cyberiadaml_builder import CGMLBuilder
from cyberiadaml_py.cyberiadaml_parser import CGMLParser
from cyberiadaml_py.types.common import Point, Rectangle
from cyberiadaml_py.types.elements import (
    CGMLElements,
    CGMLFunction,
    CGMLInput,
    CGMLOutput,
    CGMLBlock,
    CGMLTransition,
    CGMLState,
    CGMLStateMachine,
    CGMLMeta,
    CGMLInitialState,
)


def test_build_with_function_and_state_machine():
    """Test builder generates XML with both a function and a state machine."""
    # 1. Создаём функцию
    func = CGMLFunction(
        id='func_sum',
        type='function',
        parameters={'description': 'sum function'},
        inputs={
            'func_sum_input_a': CGMLInput(
                type='input',
                data='a',
                data_type='int',
                position=Rectangle(x=50, y=100, width=40, height=40)
            ),
            'func_sum_input_b': CGMLInput(
                type='input',
                data='b',
                data_type='int',
                position=Rectangle(x=50, y=200, width=40, height=40)
            )
        },
        outputs={
            'func_sum_output_result': CGMLOutput(
                type='output',
                data='result',
                data_type='int',
                position=Rectangle(x=450, y=150, width=40, height=40)
            )
        },
        body={
            'func_sum_block_Сложение': CGMLBlock(
                type='block',
                data='Сложение',
                block_type='ADD',
                position=Rectangle(x=200, y=150, width=150, height=50)
            )
        },
        edges={
            'e1': CGMLTransition(
                id='e1',
                source='func_sum_input_a',
                target='func_sum_block_Сложение',
                actions='a',
                unknown_datanodes=[]
            ),
            'e2': CGMLTransition(
                id='e2',
                source='func_sum_input_b',
                target='func_sum_block_Сложение',
                actions='b',
                unknown_datanodes=[]
            ),
            'e3': CGMLTransition(
                id='e3',
                source='func_sum_block_Сложение',
                target='func_sum_output_result',
                actions='result',
                unknown_datanodes=[]
            )
        },
        name='Функция сложения'
    )

    # 2. Создаём state machine
    sm_id = 'sm_test'
    meta = CGMLMeta(id='meta1', values={
        'platform': 'test_platform',
        'standardVersion': '1.0'
    })
    # Состояния
    states = {
        'state1': CGMLState(
            name='State 1',
            actions='entry/do_something();',
            unknown_datanodes=[],
            bounds=Rectangle(x=100, y=100, width=200, height=100),
            color='#FFFFFF'
        )
    }
    # Начальное состояние (вершина)
    initial_states = {
        'init1': CGMLInitialState(
            type='initial',
            position=Point(x=50, y=50)
        )
    }
    # Переходы
    transitions = {
        'edge1': CGMLTransition(
            id='edge1',
            source='init1',
            target='state1',
            actions='',
            unknown_datanodes=[],
            position=[Point(x=75, y=75), Point(x=100, y=75)]
        )
    }

    sm = CGMLStateMachine(
        platform='test_platform',
        meta=meta,
        standard_version='1.0',
        states=states,
        transitions=transitions,
        components={},
        notes={},
        initial_states=initial_states,
        finals={},
        choices={},
        terminates={},
        shallow_history={},
        deep_history={},
        unknown_vertexes={},
        name='Test State Machine'
    )

    # 3. Собираем CGMLElements
    elements = CGMLElements(
        state_machines={sm_id: sm},
        format='Cyberiada-GraphML-1.0',
        keys={},  # ключи могут быть пустыми, билдер добавит стандартные
        functions={'func_sum': func}
    )

    # 4. Билдер создаёт XML
    builder = CGMLBuilder()
    xml_str = builder.build(elements)

    # Сохраняем для диагностики
    with open('test_both.xml', 'w', encoding='utf-8') as f:
        f.write(xml_str)

    # 5. Парсим XML обратно
    parser = CGMLParser()
    parsed_elements = parser.parse_cgml(xml_str)

    # 6. Проверяем, что обе сущности присутствуют
    # Функция
    assert len(parsed_elements.functions) == 1
    parsed_func = parsed_elements.functions.get('func_sum')
    assert parsed_func is not None
    assert parsed_func.id == 'func_sum'
    assert len(parsed_func.inputs) == 2
    assert len(parsed_func.outputs) == 1
    assert len(parsed_func.body) == 1
    assert len(parsed_func.edges) == 3

    # State machine
    assert len(parsed_elements.state_machines) == 1
    parsed_sm = parsed_elements.state_machines.get(sm_id)
    assert parsed_sm is not None
    assert len(parsed_sm.states) == 1
    assert 'state1' in parsed_sm.states
    assert len(parsed_sm.initial_states) == 1
    assert 'init1' in parsed_sm.initial_states
    assert len(parsed_sm.transitions) == 1
    assert 'edge1' in parsed_sm.transitions
    assert parsed_sm.transitions['edge1'].source == 'init1'
    assert parsed_sm.transitions['edge1'].target == 'state1'

    # Проверяем, что в XML есть два графа с правильными id
    root = ET.fromstring(xml_str)
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    graphs = root.findall('g:graph', ns)
    graph_ids = [g.get('id') for g in graphs]
    assert 'func_sum' in graph_ids
    assert sm_id in graph_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
