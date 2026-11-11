from dataclasses import dataclass
from typing import Literal

ProbeResult = Literal["present", "absent", "unknown"]

AREA_LABELS = {"TLS": "TLS/SSL", "Network": "Network/Service", "API": "API"}


@dataclass(frozen=True)
class Scenario:
    name: str
    area: str
    expected_finding: str


@dataclass(frozen=True)
class Target:
    name: str
    base_url: str
    http_base_url: str
    approved_ports: tuple[int, ...]
    drift_ports: tuple[int, ...]
    scope: tuple[str, ...]
    scenarios: tuple[Scenario, ...]

    def finding_key(self, scenario_name: str) -> str:
        for scenario in self.scenarios:
            if scenario.name == scenario_name:
                return f"{self.name}/{scenario.area}/{scenario_name}"
        raise KeyError(scenario_name)
