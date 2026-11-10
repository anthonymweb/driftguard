"""Target modules registered with the domain controller."""
from types import ModuleType

from . import democommerce, eservices

MODULES: dict[str, ModuleType] = {
    eservices.NAME: eservices,
    democommerce.NAME: democommerce,
}
