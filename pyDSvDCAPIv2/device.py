from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from pyDSvDCAPIv2.enums import (
    Action, CapabilityType, DeviceClass, DeviceStatus, DeviceType, EventType,
)

logger = logging.getLogger(__name__)


@dataclass
class VdcCapability:
    """Represents a device capability with optional parameters.

    Note: The parameters dict is a Python-level abstraction — the proto wire
    format for DeviceAnnouncement.capabilities is a repeated enum (no parameters).
    Parameters are stored in YAML and used for user-side logic only.
    """
    type: CapabilityType
    parameters: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": int(self.type), "parameters": dict(self.parameters)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VdcCapability:
        return cls(
            type=CapabilityType(data["type"]),
            parameters=dict(data.get("parameters", {})),
        )


@dataclass
class Measurement:
    """A measurement channel reported by a device."""
    type: str
    value: float = 0.0
    unit: str = ""
    timestamp: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "value": self.value,
                "unit": self.unit, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Measurement:
        return cls(
            type=data["type"],
            value=float(data.get("value", 0.0)),
            unit=data.get("unit", ""),
            timestamp=int(data.get("timestamp", 0)),
        )


@dataclass
class Scene:
    """A scene supported by or associated with a device."""
    scene_id: str
    name: str = ""
    type: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"sceneId": self.scene_id, "name": self.name,
                "type": self.type, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scene:
        return cls(
            scene_id=data["sceneId"],
            name=data.get("name", ""),
            type=int(data.get("type", 0)),
            metadata=dict(data.get("metadata", {})),
        )


class Device:
    """Virtual device announced to dSS. Thin wrapper around DeviceAnnouncement."""

    def __init__(
        self,
        device_id: str,
        type: DeviceType,
        class_: DeviceClass,
        status: DeviceStatus,
        name: str = "",
        capabilities: list[VdcCapability] | None = None,
        config: dict[str, str] | None = None,
        metadata: dict[str, str] | None = None,
        attributes: dict[str, str] | None = None,
        measurements: list[Measurement] | None = None,
        scenes: list[Scene] | None = None,
    ) -> None:
        self.device_id = device_id
        self.type = type
        self.class_ = class_
        self.status = status
        self.name = name
        self.capabilities: list[VdcCapability] = capabilities or []
        self.config: dict[str, str] = config or {}
        self.metadata: dict[str, str] = metadata or {}
        self.attributes: dict[str, str] = attributes or {}
        self.measurements: list[Measurement] = measurements or []
        self.scenes: list[Scene] = scenes or []
        self.state: dict[str, str] = {}

        # Callbacks — set by user
        self.on_set_state: Callable[[str, str], Awaitable[None]] | None = None
        self.on_get_state: Callable[[str], Awaitable[str]] | None = None
        self.on_command: Callable[[str, dict], Awaitable[dict]] | None = None
        self.on_scene: Callable[[str, Action, dict], Awaitable[None]] | None = None
        self.on_firmware_update: Callable[[str, str], Awaitable[None]] | None = None

        # Set by VDC on registration
        self._vdc: Any = None

    def update_state(self, attribute: str, value: str) -> None:
        """Update a local state attribute and schedule auto-save."""
        self.state[attribute] = value
        if self._vdc is not None:
            self._vdc._schedule_save()

    async def send_event(
        self,
        event_type: EventType,
        attribute: str = "",
        value: str = "",
    ) -> None:
        """Send a DeviceEvent to dSS."""
        if self._vdc is not None:
            await self._vdc._send_device_event(self, event_type, attribute, value)
        else:
            logger.warning("Device %s not registered with a VDC", self.device_id)

    async def remove(self) -> None:
        """Send DeviceRemoval to dSS and deregister from VDC."""
        if self._vdc is not None:
            await self._vdc.remove_device(self.device_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "type": int(self.type),
            "class_": int(self.class_),
            "status": int(self.status),
            "name": self.name,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "config": dict(self.config),
            "metadata": dict(self.metadata),
            "attributes": dict(self.attributes),
            "measurements": [m.to_dict() for m in self.measurements],
            "scenes": [s.to_dict() for s in self.scenes],
            "state": dict(self.state),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        d = cls(
            device_id=data["device_id"],
            type=DeviceType(data["type"]),
            class_=DeviceClass(data["class_"]),
            status=DeviceStatus(data["status"]),
            name=data.get("name", ""),
            capabilities=[VdcCapability.from_dict(c) for c in data.get("capabilities", [])],
            config=dict(data.get("config", {})),
            metadata=dict(data.get("metadata", {})),
            attributes=dict(data.get("attributes", {})),
            measurements=[Measurement.from_dict(m) for m in data.get("measurements", [])],
            scenes=[Scene.from_dict(s) for s in data.get("scenes", [])],
        )
        d.state = dict(data.get("state", {}))
        return d
