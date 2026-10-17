# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The enums and the constants of the CyberiadaML interface
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
"""The enums and the constants of the CyberiadaML interface."""
import enum


class _Enum(enum.IntEnum):
    """An enum of the binding: an int that prints its member name."""

    def __str__(self) -> str:
        return '%s.%s' % (type(self).__name__, self.name)


class ElementType(_Enum):
    """The element types."""

    elementRoot = 0
    elementSM = 1
    elementSimpleState = 2
    elementCompositeState = 3
    elementComment = 4
    elementFormalComment = 5
    elementInitial = 6
    elementFinal = 7
    elementChoice = 8
    elementTerminate = 9
    elementTransition = 10
    elementShallowHistory = 11
    elementDeepHistory = 12
    elementSubmachineState = 13
    elementEntryPoint = 14
    elementExitPoint = 15


class TransitionType(_Enum):
    """The transition types."""

    transitionExternal = 0
    transitionLocal = 1


class DocumentFormat(_Enum):
    """The document formats."""

    formatCyberiada10 = 0
    formatLegacyYED = 1
    formatLegacyYEDOstranna = 2
    formatLegacyYEDBerloga16 = 3
    formatLapki = 4
    formatDetect = 99


class DocumentGeometryFormat(_Enum):
    """The geometry formats."""

    geometryFormatNone = 0
    geometryFormatLegacyYED = 1
    geometryFormatCyberiada10 = 2
    geometryFormatQt = 3


class CommentSubjectType(_Enum):
    """The kinds of the comment subjects."""

    commentSubjectElement = 0
    commentSubjectName = 1
    commentSubjectData = 2


class ActionType(_Enum):
    """The action types."""

    actionTransition = 0
    actionEntry = 1
    actionExit = 2


class EventPropagation(_Enum):
    """The event propagation of an action."""

    eventPropagationNone = 0
    eventPropagationBlock = 1
    eventPropagationPropagate = 2
    eventPropagationDefer = 3


class DocumentTransitionOrder(_Enum):
    """The transition order of the document."""

    transitionOrderNone = 0
    transitionOrderAction = 1
    transitionOrderExit = 2


class DocumentEventPropagation(_Enum):
    """The event propagation of the document."""

    docEventPropagationNone = 0
    docEventPropagationBlock = 1
    docEventPropagationPropagate = 2


class DocumentGeometryDeclaration(_Enum):
    """The geometry declared by the metadata."""

    geometryDeclarationAbsent = 0
    geometryDeclarationNone = 1
    geometryDeclarationShort = 2
    geometryDeclarationFull = 3


# the members at the module level, as the binding exports them
elementRoot = ElementType.elementRoot
elementSM = ElementType.elementSM
elementSimpleState = ElementType.elementSimpleState
elementCompositeState = ElementType.elementCompositeState
elementComment = ElementType.elementComment
elementFormalComment = ElementType.elementFormalComment
elementInitial = ElementType.elementInitial
elementFinal = ElementType.elementFinal
elementChoice = ElementType.elementChoice
elementTerminate = ElementType.elementTerminate
elementTransition = ElementType.elementTransition
elementShallowHistory = ElementType.elementShallowHistory
elementDeepHistory = ElementType.elementDeepHistory
elementSubmachineState = ElementType.elementSubmachineState
elementEntryPoint = ElementType.elementEntryPoint
elementExitPoint = ElementType.elementExitPoint
transitionExternal = TransitionType.transitionExternal
transitionLocal = TransitionType.transitionLocal
formatCyberiada10 = DocumentFormat.formatCyberiada10
formatLegacyYED = DocumentFormat.formatLegacyYED
formatLegacyYEDOstranna = DocumentFormat.formatLegacyYEDOstranna
formatLegacyYEDBerloga16 = DocumentFormat.formatLegacyYEDBerloga16
formatLapki = DocumentFormat.formatLapki
formatDetect = DocumentFormat.formatDetect
geometryFormatNone = DocumentGeometryFormat.geometryFormatNone
geometryFormatLegacyYED = DocumentGeometryFormat.geometryFormatLegacyYED
geometryFormatCyberiada10 = DocumentGeometryFormat.geometryFormatCyberiada10
geometryFormatQt = DocumentGeometryFormat.geometryFormatQt
commentSubjectElement = CommentSubjectType.commentSubjectElement
commentSubjectName = CommentSubjectType.commentSubjectName
commentSubjectData = CommentSubjectType.commentSubjectData
actionTransition = ActionType.actionTransition
actionEntry = ActionType.actionEntry
actionExit = ActionType.actionExit
eventPropagationNone = EventPropagation.eventPropagationNone
eventPropagationBlock = EventPropagation.eventPropagationBlock
eventPropagationPropagate = EventPropagation.eventPropagationPropagate
eventPropagationDefer = EventPropagation.eventPropagationDefer
transitionOrderNone = DocumentTransitionOrder.transitionOrderNone
transitionOrderAction = DocumentTransitionOrder.transitionOrderAction
transitionOrderExit = DocumentTransitionOrder.transitionOrderExit
docEventPropagationNone = DocumentEventPropagation.docEventPropagationNone
docEventPropagationBlock = DocumentEventPropagation.docEventPropagationBlock
docEventPropagationPropagate = \
    DocumentEventPropagation.docEventPropagationPropagate
geometryDeclarationAbsent = \
    DocumentGeometryDeclaration.geometryDeclarationAbsent
geometryDeclarationNone = DocumentGeometryDeclaration.geometryDeclarationNone
geometryDeclarationShort = DocumentGeometryDeclaration.geometryDeclarationShort
geometryDeclarationFull = DocumentGeometryDeclaration.geometryDeclarationFull

QUALIFIED_NAME_SEPARATOR = '::'

# the differences of two action lists (compare_actions)
adiffArguments = 1
adiffOrder = 2
adiffActions = 4
adiffTypes = 16
adiffGuards = 32
adiffNumber = 64
adiffPropagation = 128

# the isomorphism results and the difference flags
smiIdentical = 1
smiEqual = 2
smiIsomorphic = 4
smiDiffStates = 8
smiDiffInitial = 16
smiDiffEdges = 32
smiNodeDiffFlagID = 1
smiNodeDiffFlagType = 2
smiNodeDiffFlagTitle = 4
smiNodeDiffFlagActions = 8
smiNodeDiffFlagSMLink = 16
smiNodeDiffFlagChildren = 32
smiNodeDiffFlagEdges = 64
smiEdgeDiffFlagID = 128
smiEdgeDiffFlagAction = 256
