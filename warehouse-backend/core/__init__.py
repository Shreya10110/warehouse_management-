"""Application core package.

The compatibility aliases preserve the established module imports while the
implementation itself is organised under ``core``.  This makes the layout
change safe for the existing routes, services, scripts, and tests.
"""

from importlib import import_module
import sys

for _name in ("models", "cruds", "services", "dependencies", "controllers", "utils"):
    sys.modules.setdefault(_name, import_module(f".{_name}", __name__))

# Schemas live beside routes as part of the public API layer.
sys.modules.setdefault("schemas", import_module(".apis.schemas", __name__))
