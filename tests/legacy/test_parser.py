"""Module with tests of CGMLParser."""
from pprint import pprint

import pytest
from cyberiadaml_py.cyberiadaml_builder import CGMLBuilder
from cyberiadaml_py.cyberiadaml_parser import CGMLParser
from cyberiadaml_py.types.elements import CGMLElements


@pytest.fixture
def blinker():
    """Return raw Arduino-blinker scheme."""
    with open('demos/CyberiadaFormat-Blinker.graphml') as f:
        data = f.read()
        return data


def test_parse(blinker: str):
    """Test parse_cgml function."""
    parser = CGMLParser()
    elements = parser.parse_cgml(blinker)
    pprint(elements)


@pytest.mark.parametrize(
    'path', [
        # pytest.param(
        #     'demos/CyberiadaFormat-Autoborder.graphml',
        #     id='Bearloga'
        # ),
        # pytest.param(
        #     'demos/two-blinkers.graphml',
        #     id='Two blinkers'
        # ),
        # pytest.param(
        #     'demos/CyberiadaFormat-Blinker.graphml',
        #     id='ArduinoUno'
        # ),
        pytest.param(
            'demos/with-shallow-history.graphml',
            id='shallow history'
        )
    ]
)
def test_parse_build_cycle(path: str) -> None:
    """Test parse-build cycle."""
    parser = CGMLParser()
    builder = CGMLBuilder()

    with open(path) as demo:
        data: str = demo.read()
        elements: CGMLElements = parser.parse_cgml(data)
        builded: str = builder.build(elements)
        print(builded)
        print(elements)
        # На случай, если тест не проходится
        # with open('elements.json', 'w') as f:
        #     f.write(elements.model_dump_json(indent=4))
        # with open('test.graphml', 'w') as f:
        #     f.write(builded)
        new_elements: CGMLElements = parser.parse_cgml(builded)
        # with open('new_elements.json', 'w') as f:
        #     f.write(new_elements.model_dump_json(indent=4))
        assert new_elements == elements
