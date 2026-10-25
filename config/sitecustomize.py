"""Monkey-patch Django's copy.copy for Python 3.14 compatibility."""

import copy
from django.template.context import Context

_original_copy = copy.copy


def _patched_copy(obj):
    """Handle Django Context objects that fail to copy in Python 3.14."""
    if isinstance(obj, Context):
        return Context(list(obj.dicts))
    return _original_copy(obj)


copy.copy = _patched_copy
