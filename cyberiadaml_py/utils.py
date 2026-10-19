"""Module implements small utility functions."""
from typing import List, Optional, TypeVar, Union

ListType = TypeVar('ListType')


def to_list(
    nodes: Optional[Union[List[ListType], ListType]]
) -> List[ListType]:
    """Return list of objects."""
    if nodes is None:
        return []
    if isinstance(nodes, list):
        return nodes
    else:
        return [nodes]
