# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The appendix B key inventory and the standard value enumerations
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
"""The appendix B key inventory and the standard value enumerations."""
# (key id, for) -> attr.name, per the appendix B table of the standard
STANDARD_BINDINGS = {
    ('gFormat', 'graphml'): 'format',
    ('dName', 'graph'): 'name',
    ('dName', 'node'): 'name',
    ('dStateMachine', 'graph'): 'stateMachine',
    ('dRegion', 'graph'): 'region',
    ('dSubmachineState', 'node'): 'submachineState',
    ('dGeometry', 'graph'): 'geometry',
    ('dGeometry', 'node'): 'geometry',
    ('dGeometry', 'edge'): 'geometry',
    ('dSourcePoint', 'edge'): 'sourcePoint',
    ('dTargetPoint', 'edge'): 'targetPoint',
    ('dLabelGeometry', 'edge'): 'labelGeometry',
    ('dNote', 'node'): 'note',
    ('dVertex', 'node'): 'vertex',
    ('dData', 'node'): 'data',
    ('dData', 'edge'): 'data',
    ('dPivot', 'edge'): 'pivot',
    ('dChunk', 'edge'): 'chunk',
    ('dCollapsed', 'node'): 'collapsed',
    ('dMarkup', 'node'): 'markup',
    ('dColor', 'node'): 'color',
    ('dColor', 'edge'): 'color',
    ('dFormalName', 'graph'): 'formalName',
    ('dFormalName', 'node'): 'formalName',
}

STANDARD_KEY_IDS = frozenset(key for key, _ in STANDARD_BINDINGS)

# the appendix B keys declared without attr.type; every other one is a string
UNTYPED_KEYS = frozenset(('dGeometry', 'dSourcePoint', 'dTargetPoint',
                          'dLabelGeometry'))

# 9.2: the CSS/HTML named colours (CSS Color Module Level 4)
CSS_COLOR_NAMES = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond
blue blueviolet brown burlywood cadetblue chartreuse chocolate coral
cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray
darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey
darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue
firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod
gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki
lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon
lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue
lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue
mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen
mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod
palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum
powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon
sandybrown seagreen seashell sienna silver skyblue slateblue slategray
slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet
wheat white whitesmoke yellow yellowgreen
""".split())

VERTEX_CORE = ('initial', 'final', 'choice', 'terminate')
VERTEX_EXT = ('shallowHistory', 'deepHistory', 'entryPoint', 'exitPoint')
VERTEX_RESERVED = ('fork', 'join')

NOTE_KINDS = ('informal', 'formal')

GEOMETRY_MODES = ('none', 'short', 'full')
TRANSITION_ORDERS = ('actionFirst', 'exitFirst')
EVENT_PROPAGATIONS = ('block', 'propagate')
