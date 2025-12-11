"""Form generation strategies.

This package contains strategy classes for generating form contexts.
Each strategy handles a specific pattern of form generation.
"""
from model_builder.adapters.forms.strategies.base import FormStrategy
from model_builder.adapters.forms.strategies.simple import SimpleFormStrategy
from model_builder.adapters.forms.strategies.with_storage import WithStorageFormStrategy
from model_builder.adapters.forms.strategies.child_of_parent import ChildOfParentFormStrategy
from model_builder.adapters.forms.strategies.parent_selection import ParentSelectionFormStrategy
from model_builder.adapters.forms.strategies.nested_parent_selection import NestedParentSelectionFormStrategy

__all__ = [
    'FormStrategy',
    'SimpleFormStrategy',
    'WithStorageFormStrategy',
    'ChildOfParentFormStrategy',
    'ParentSelectionFormStrategy',
    'NestedParentSelectionFormStrategy',
]
