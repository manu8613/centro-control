"""Shared test setup.

The calculation modules (energy, tariff, problems, panel...) do not import
Home Assistant, so they can be tested without it. When Home Assistant is not
installed, the package is registered without running its ``__init__``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "centro_control"

if importlib.util.find_spec("homeassistant") is None:  # pragma: no cover - local runs
    parent = types.ModuleType("custom_components")
    parent.__path__ = [str(PACKAGE.parent)]
    pkg = types.ModuleType("custom_components.centro_control")
    pkg.__path__ = [str(PACKAGE)]
    sys.modules.setdefault("custom_components", parent)
    sys.modules.setdefault("custom_components.centro_control", pkg)
