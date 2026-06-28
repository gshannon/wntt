"""
WSGI config for wnttapi project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SET-ME-CORRECTLY")

if os.environ.get("DEBUGPY_ENABLE") == "1":
    import debugpy

    debugpy.listen(("0.0.0.0", 5678))
    print("debugpy listening on 5678", flush=True)
    debugpy.wait_for_client()
    print("Debugger attached!", flush=True)


application = get_wsgi_application()
