"""Custom test runner that patches Django's template context copying bug."""

import copy
from django.template.context import Context
from django.test import client
from django.test.runner import DiscoverRunner
from django.test.utils import template_rendered


def patched_store_rendered_templates(*args, **kwargs):
    """Patched version that handles Python 3.14 copy issues for Django Context."""
    try:
        # args: (sender, template, context)
        if len(args) >= 3:
            sender, template, context = args[0], args[1], args[2]
        else:
            sender = kwargs.get("sender")
            template = kwargs.get("template")
            context = kwargs.get("context")

        store = getattr(sender, "_context_stores", None)
        if store is not None:
            if isinstance(context, Context):
                store["context"].append(Context(list(context.dicts)))
            else:
                store["context"].append(copy.copy(context))
    except (AttributeError, TypeError):
        pass


class CustomTestRunner(DiscoverRunner):
    """Test runner that patches the template context copying bug in Django 5.0 + Python 3.14."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        client.store_rendered_templates = patched_store_rendered_templates

    def teardown_test_environment(self, **kwargs):
        import importlib
        import django.test.client as client_module
        importlib.reload(client_module)
        super().teardown_test_environment(**kwargs)
