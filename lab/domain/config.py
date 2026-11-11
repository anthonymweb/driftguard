"""Target registry: builds ``TARGETS`` from the explicit module list."""
from .model import Target
from .targets import MODULES

TARGETS: dict[str, Target] = {name: mod.TARGET for name, mod in MODULES.items()}


def get(name: str) -> Target:
    return TARGETS[name]
