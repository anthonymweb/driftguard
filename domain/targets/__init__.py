"""Target modules registered with the domain controller."""
from types import ModuleType

from . import eservices

MODULES: dict[str, ModuleType] = {
    eservices.NAME: eservices,
}
