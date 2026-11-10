"""Target modules registered with the domain controller."""
from types import ModuleType

from . import civicportal, democommerce, eservices

MODULES: dict[str, ModuleType] = {
    eservices.NAME: eservices,
    democommerce.NAME: democommerce,
    civicportal.NAME: civicportal,
}
