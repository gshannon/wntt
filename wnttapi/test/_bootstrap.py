"""Configure Django once for the test suite.

Every ``test_*.py`` module that imports ``app.*`` must import this module first::

    import test._bootstrap  # noqa: F401

``import test._bootstrap`` resolves for both discovery modes (bare
``unittest discover -s test`` and package-qualified ``python -m unittest
test.test_x``) because ``wnttapi/`` is always on ``sys.path`` as the cwd.
``django.setup()`` is idempotent, so importing this from many modules is safe.

Do NOT do expensive work (station loads, disk / cache I/O) at module scope in a
test module -- put it in ``setUpClass``.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")

import django

django.setup()
