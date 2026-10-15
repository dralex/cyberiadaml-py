"""Tests for function graph generation using builder and parser."""
import xml.etree.ElementTree as ET

import pytest
from cyberiadaml_py.cyberiadaml_builder import CGMLBuilder
from cyberiadaml_py.cyberiadaml_parser import CGMLParser
from cyberiadaml_py.types.common import Rectangle
from cyberiadaml_py.types.elements import (
    CGMLElements,
    CGMLFunction,
    CGMLInput,
    CGMLOutput,
    CGMLBlock,
    CGMLTransition,
)


def test_build_and_parse_function():
    """Test building a function graph and then parsing it back."""
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

    elements = CGMLElements(
        state_machines={},
        format='Cyberiada-GraphML-1.0',
        keys={},
        functions={'func_sum': func}
    )

    builder = CGMLBuilder()
    xml_str = builder.build(elements)

    # Сохраняем для диагностики
    with open('func_sum.xml', 'w', encoding='utf-8') as f:
        f.write(xml_str)

    # Проверяем, что XML содержит все рёбра
    root = ET.fromstring(xml_str)
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    graph = root.find(".//g:graph[@id='func_sum']", ns)
    assert graph is not None
    edges_xml = graph.findall('g:edge', ns)
    assert len(edges_xml) == 3, (
        f'Expected 3 edges in XML, got {len(edges_xml)}'
    )

    # Парсим обратно
    parser = CGMLParser()
    parsed_elements = parser.parse_cgml(xml_str)

    # Проверяем, что распарсена одна функция
    assert len(parsed_elements.functions) == 1
    parsed_func = parsed_elements.functions.get('func_sum')
    assert parsed_func is not None
    assert parsed_func.id == 'func_sum'
    assert parsed_func.type == 'function'
    assert parsed_func.parameters.get('description') == 'sum function'

    # Проверяем входы
    assert len(parsed_func.inputs) == 2
    assert 'func_sum_input_a' in parsed_func.inputs
    assert 'func_sum_input_b' in parsed_func.inputs
    assert parsed_func.inputs['func_sum_input_a'].data == 'a'
    assert parsed_func.inputs['func_sum_input_a'].data_type == 'int'
    assert parsed_func.inputs['func_sum_input_b'].data == 'b'

    # Проверяем выходы
    assert len(parsed_func.outputs) == 1
    assert 'func_sum_output_result' in parsed_func.outputs
    assert parsed_func.outputs['func_sum_output_result'].data == 'result'

    # Проверяем блоки
    assert len(parsed_func.body) == 1
    assert 'func_sum_block_Сложение' in parsed_func.body
    assert parsed_func.body['func_sum_block_Сложение'].block_type == 'ADD'

    # Проверяем рёбра
    assert len(parsed_func.edges) == 3
    assert 'e1' in parsed_func.edges
    assert parsed_func.edges['e1'].source == 'func_sum_input_a'
    assert parsed_func.edges['e1'].target == 'func_sum_block_Сложение'
    assert parsed_func.edges['e1'].actions == 'a'

    # Проверяем геометрию
    input_a_pos = parsed_func.inputs['func_sum_input_a'].position
    assert input_a_pos is not None
    assert input_a_pos.x == 50
    assert input_a_pos.y == 100

    print('test_build_and_parse_function passed')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
