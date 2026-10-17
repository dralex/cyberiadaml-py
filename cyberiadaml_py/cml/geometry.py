# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The geometry values of the CyberiadaML interface
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
"""The geometry values: Point, Rect and Polyline."""
from typing import Any, Iterable, List, Optional

# the tolerance of Rect.almost_equal (the C++ EQUAL_DIFF)
EQUAL_DIFF = 0.001
# the value of geometryFormatQt (the rects are centred there)
QT_FORMAT = 3


def number(value: float) -> str:
    """Return a coordinate as the C++ stream prints it (6 digits)."""
    return format(value, 'g')


def truncate(value: float) -> float:
    """Return the value rounded as the C++ round() does: truncated."""
    return float(int(value))


class Point:
    """A point; Point() is not valid."""

    def __init__(self, x: Optional[float] = None,
                 y: Optional[float] = None) -> None:
        self.valid = x is not None and y is not None
        self.x = float(x) if x is not None else 0.0
        self.y = float(y) if y is not None else 0.0

    def round(self) -> None:
        if self.valid:
            self.x, self.y = truncate(self.x), truncate(self.y)

    def copy(self) -> 'Point':
        return Point(self.x, self.y) if self.valid else Point()

    def __repr__(self) -> str:
        if not self.valid:
            return '()'
        return '(%s; %s)' % (number(self.x), number(self.y))


class Rect:
    """A rect; Rect() is not valid."""

    def __init__(self, x: Optional[float] = None, y: Optional[float] = None,
                 width: Optional[float] = None,
                 height: Optional[float] = None) -> None:
        self.valid = None not in (x, y, width, height)
        self.x = float(x) if x is not None else 0.0
        self.y = float(y) if y is not None else 0.0
        self.width = float(width) if width is not None else 0.0
        self.height = float(height) if height is not None else 0.0

    def round(self) -> None:
        if self.valid:
            self.x, self.y = truncate(self.x), truncate(self.y)
            self.width = truncate(self.width)
            self.height = truncate(self.height)

    def almost_equal(self, other: 'Rect') -> bool:
        if not self.valid or not other.valid:
            return self.valid == other.valid
        return all(abs(a - b) < EQUAL_DIFF for a, b in (
            (self.x, other.x), (self.y, other.y),
            (self.width, other.width), (self.height, other.height)))

    def expand(self, value: Any, document: Any) -> None:
        """Grow to hold a point, a rect or a polyline of the document."""
        qt = int(document.get_geometry_format()) == QT_FORMAT
        if isinstance(value, Polyline):
            for point in value:
                self.expand(point, document)
        elif isinstance(value, Rect):
            if not value.valid:
                return
            if not self.valid:
                self.__init__(value.x, value.y,  # type: ignore[misc]
                              value.width, value.height)
            elif qt:
                half_w, half_h = value.width / 2.0, value.height / 2.0
                self.expand(Point(value.x - half_w, value.y - half_h),
                            document)
                self.expand(Point(value.x + half_w, value.y + half_h),
                            document)
            else:
                self.expand(Point(value.x, value.y), document)
                self.expand(Point(value.x + value.width,
                                  value.y + value.height), document)
        elif value.valid:
            if not self.valid:
                self.__init__(value.x, value.y, 0, 0)  # type: ignore[misc]
            elif qt:
                self.x, self.width = _grow_centred(self.x, self.width,
                                                   value.x)
                self.y, self.height = _grow_centred(self.y, self.height,
                                                    value.y)
            else:
                self.x, self.width = _grow(self.x, self.width, value.x)
                self.y, self.height = _grow(self.y, self.height, value.y)

    def copy(self) -> 'Rect':
        if not self.valid:
            return Rect()
        return Rect(self.x, self.y, self.width, self.height)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rect):
            return NotImplemented
        return (self.valid, self.x, self.y, self.width, self.height) == \
            (other.valid, other.x, other.y, other.width, other.height)

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        if not self.valid:
            return '()'
        return '(%s; %s; %s; %s)' % (number(self.x), number(self.y),
                                     number(self.width), number(self.height))


def _grow_centred(centre: float, size: float, value: float):
    half = size / 2.0
    if value < centre - half:
        delta = centre - half - value
        return centre - delta / 2.0, size + delta
    if value > centre + half:
        delta = value - centre - half
        return centre + delta / 2.0, size + delta
    return centre, size


def _grow(start: float, size: float, value: float):
    if value < start:
        return value, size + start - value
    if value > start + size:
        return start, value - start
    return start, size


class Polyline:
    """A list of points; an item read is a copy."""

    def __init__(self, points: Optional[Iterable[Point]] = None) -> None:
        self._points: List[Point] = [p.copy() for p in points or []]

    def append(self, point: Point) -> None:
        self._points.append(point.copy())

    def round(self) -> None:
        for point in self._points:
            point.round()

    def copy(self) -> 'Polyline':
        return Polyline(self._points)

    def __getitem__(self, index: int) -> Point:
        if index < 0:
            raise TypeError('a non-negative index is expected')
        return self._points[index].copy()

    def __setitem__(self, index: int, point: Point) -> None:
        self._points[index] = point.copy()

    def __iter__(self):
        return iter([p.copy() for p in self._points])

    def __len__(self) -> int:
        return len(self._points)

    def __repr__(self) -> str:
        return '[ %s ]' % ', '.join(repr(p) for p in self._points)
