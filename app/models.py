from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional
import uuid


@dataclass
class Location:
    name: str
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    source: str = "search"  # search / device / legacy


@dataclass
class Monitor:
    location: Location
    condition: str  # "above" or "below"
    threshold: float
    humidity_enabled: bool = False
    humidity_condition: str = "below"  # "above" or "below"
    humidity_threshold: float = 75.0
    enabled: bool = True
    active: Optional[bool] = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "location": asdict(self.location),
            "condition": self.condition,
            "threshold": self.threshold,
            "humidity_enabled": self.humidity_enabled,
            "humidity_condition": self.humidity_condition,
            "humidity_threshold": self.humidity_threshold,
            "enabled": self.enabled,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Monitor":
        return cls(
            id=data.get("id", ""),
            location=Location(**data["location"]),
            condition=data["condition"],
            threshold=float(data["threshold"]),
            humidity_enabled=bool(data.get("humidity_enabled", False)),
            humidity_condition=data.get("humidity_condition", "below"),
            humidity_threshold=float(data.get("humidity_threshold", 75.0)),
            enabled=bool(data.get("enabled", True)),
            active=data.get("active"),
        )
