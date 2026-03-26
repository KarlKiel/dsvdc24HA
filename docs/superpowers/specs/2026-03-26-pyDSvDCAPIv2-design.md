# pyDSvDCAPIv2 — Design Specification

**Date:** 2026-03-26
**Project:** `pyDSvDCAPIv2` — Python library for the digitalSTROM VDC API v2
**Location:** `C:\Users\I064071\VSC-projects\dsvdc24HA\dsvdc24HA\`

---

## 1. Purpose and Scope

A Python library that implements the digitalSTROM Virtual Device Connector (VDC) API v2, allowing users to easily create a fully working Python-based VDC that manages virtual devices over their complete lifecycle. The library provides:

- A gRPC client connecting to the digitalSTROM Server (dSS)
- Device announcement, update, and removal lifecycle
- Incoming command/state handling via async callbacks
- YAML-based persistence with backup/restore
- Automatic reconnection with full re-announcement
- Periodic heartbeat keepalive

**Not in scope:** The library does not implement a gRPC server. It is purely a client that connects to dSS.

---

## 2. Protocol Reference

The API v2 specification is at:
`C:\Users\I064071\VSC-projects\vdc2documentation\digitalstrom4HA\vdc_documentation\derivedProtoFiles\`

Key facts:
- **Transport:** gRPC (primary), proto3, package `digitalstrom.vdc.api.v2`
- **Connection direction:** VDC connects *to* dSS (default port 62000)
- **Completely incompatible with v1** — v1 uses a single TCP socket with a custom property-tree protobuf; v2 uses proper gRPC with well-typed messages

---

## 3. Module Structure

```
pyDSvDCAPIv2/
├── pyDSvDCAPIv2/
│   ├── __init__.py              # Public API: VDC, Device, enums, exceptions
│   ├── vdc.py                   # VDC class — top-level entry point
│   ├── device.py                # Device class — thin wrapper around DeviceAnnouncement
│   ├── dsuid.py                 # dSUID-conformant ID generation (UUID v5, namespaced)
│   ├── connection.py            # gRPC channel, stub calls, reconnect loop
│   ├── heartbeat.py             # Periodic heartbeat asyncio task
│   ├── persistence.py           # YAML load/save with atomic write + .bak backup
│   ├── enums.py                 # Python enums re-exporting proto enum values
│   ├── exceptions.py            # VDCConnectionError, DeviceError
│   └── proto/
│       └── *_pb2*.py            # Pre-generated gRPC stubs (committed to repo)
├── examples/
│   └── simple_light.py          # Minimal working example
├── tests/
├── pyproject.toml
└── README.md
```

**Proto files** (`.proto` sources) are excluded from the repo via `.gitignore`. Only the generated `*_pb2.py` stubs are committed. The proto sources live at the reference location above.

---

## 4. VDC Class

The single user-facing entry point.

```python
vdc = VDC(
    vdc_id="my-vdc-001",          # seed for dSUID generation; actual dSUID stored in YAML
    name="My Home Bridge",
    version="1.0.0",
    server_host="192.168.1.10",
    server_port=62000,
    capabilities=[VdcCapability.SCENES, VdcCapability.DYNAMIC_DEVICES],
    state_path="state.yaml",
    heartbeat_interval=30,         # seconds, default 30
)

vdc.add_device(device)
vdc.remove_device(device_id)      # removes from registry; sends DeviceRemoval if connected

await vdc.start()                  # connect, announce, start background tasks
await vdc.stop()                   # graceful shutdown
await vdc.flush()                  # force immediate YAML save

# VDC-level event callbacks:
vdc.on_device_event = async_callback   # (DeviceEvent) from StreamDeviceEvents
vdc.on_scene_event  = async_callback   # (SceneEvent) from StreamSceneEvents
```

On `start()`:
1. Load YAML state (restore vdc_id and devices)
2. Open gRPC channel
3. Call `Announce()` — send `ServiceAnnouncement`, receive `ServiceAcknowledgement`
4. Call `RegisterDevice()` stream — send `DeviceAnnouncement` for each device
5. Start `StreamDeviceEvents()` background task
6. Start `StreamSceneEvents()` background task
7. Start heartbeat background task

---

## 5. Device Class

Thin wrapper matching the `DeviceAnnouncement` proto exactly.

```python
device = Device(
    device_id="lamp-001",          # seed for dSUID; actual dSUID stored in YAML
    type=DeviceType.LIGHT,
    class_=DeviceClass.LIGHTING,
    name="Kitchen Light",
    status=DeviceStatus.ONLINE,
    capabilities=[VdcCapability(type=CapabilityType.DIMMING)],
    config={"address": "110120301A1A", "model": "dS21-400"},
    attributes={},
    metadata={},
    measurements=[],
    scenes=[],
)

# Incoming callbacks (called by library when dSS sends a message for this device):
device.on_set_state = async def(attribute: str, value: str) -> None
device.on_get_state = async def(attribute: str) -> str
device.on_command   = async def(command: str, params: dict) -> dict
device.on_scene     = async def(scene_id: str, action: Action, params: dict) -> None

# Outgoing — push state/events to dSS:
await device.update_state("brightness", "75")   # updates local state dict + triggers auto-save
                                                 # NOTE: does NOT send SetStateRequest to dSS;
                                                 # SetStateRequest flows dSS→VDC (via on_set_state)
await device.send_event(                         # sends DeviceEvent via StreamDeviceEvents
    EventType.VALUE_REPORTED,
    attribute="brightness",
    value="75"
)
await device.remove()                            # sends DeviceRemoval, removes from VDC
```

Devices hold a `state: dict[str, str]` — the last-known attribute values. This is persisted to YAML and restored on startup.

---

## 6. dSUID-Conformant ID Generation (`dsuid.py`)

IDs are generated deterministically using UUID v5 (name-based SHA-1) within fixed namespaces, formatted as a 17-byte (34 hex char) dSUID string — matching the digitalSTROM ecosystem convention.

```python
# Namespaces (fixed UUIDs, one per entity type):
VDC_NAMESPACE    = UUID("...")
DEVICE_NAMESPACE = UUID("...")

class DsUid:
    @staticmethod
    def for_vdc(seed: str) -> str:
        """Generate stable dSUID for a VDC from a seed string."""

    @staticmethod
    def for_device(seed: str) -> str:
        """Generate stable dSUID for a device from a seed string."""
```

On first `VDC.start()`:
- If `state.yaml` exists and contains a `vdc_id`, use that (stable across restarts)
- Otherwise generate from the seed, save to YAML

Same logic for each `Device.device_id`.

---

## 7. Persistence (`persistence.py`)

**What is persisted:**
- VDC: `vdc_id` (resolved dSUID), `name`, `version`, `server_host`, `server_port`, `capabilities`
- Each device: all `DeviceAnnouncement` fields + `state` dict (last-known attribute values)

**YAML structure:**
```yaml
vdc:
  vdc_id: "0101020304050607080910111213141516"
  name: "My Home Bridge"
  version: "1.0.0"
  server_host: "192.168.1.10"
  server_port: 62000
  capabilities: [0, 4]

devices:
  - device_id: "0101020304050607080910111213141516"
    type: 0
    class_: 0
    name: "Kitchen Light"
    status: 0
    config:
      address: "110120301A1A"
      model: "dS21-400"
    capabilities:
      - type: 1
        parameters: {}
    metadata: {}
    attributes: {}
    measurements: []
    scenes: []
    state:
      brightness: "75"
      on: "true"
```

**Write strategy (atomic):**
1. Serialize to `state.yaml.tmp`
2. Move `state.yaml` → `state.yaml.bak`
3. Rename `state.yaml.tmp` → `state.yaml`

**Load strategy:**
1. Try `state.yaml`
2. Fallback to `state.yaml.bak`
3. Start fresh if neither exists

**Auto-save:** debounced 1-second delay after any state mutation. `vdc.flush()` forces immediate save.

---

## 8. Connection Management (`connection.py`)

Owns the gRPC channel and all stub calls. Implements reconnect loop.

**Reconnect strategy:** exponential backoff starting at 2s, doubling each attempt, capped at 60s.

**On disconnect/error:**
1. Cancel all background tasks (heartbeat, event streams)
2. Wait backoff delay
3. Re-open gRPC channel
4. Re-run full announce + register sequence
5. Restart background tasks

**Background tasks (all asyncio tasks):**
- `StreamDeviceEvents` listener → dispatches to `device.on_command`, `device.on_set_state`, `device.on_get_state`, `device.on_scene` per device_id
- `StreamSceneEvents` listener → dispatches to `vdc.on_scene_event`
- Heartbeat loop

---

## 9. Heartbeat (`heartbeat.py`)

Simple asyncio loop:
```python
while running:
    await stub.Heartbeat(Heartbeat(vdc_id=vdc_id, timestamp=now_ms()))
    await asyncio.sleep(interval)
```

Optional `metrics` map can be populated by the user via `vdc.heartbeat_metrics: dict`.

---

## 10. Error Handling

- `VDCConnectionError` — raised from `start()` if handshake fails (auth rejected, version mismatch)
- `DeviceError` — raised if `SetStateResponse` or `CommandResult` returns non-OK status
- gRPC transport errors → logged + trigger reconnect loop (never propagated to user)
- User callback exceptions → logged, do not crash the VDC

---

## 11. Enums (`enums.py`)

Python `IntEnum` classes wrapping proto enum values, so users never need to import from `_pb2` directly:

```python
class DeviceType(IntEnum):
    LIGHT = 0; SWITCH = 1; SHUTTER = 2; THERMOSTAT = 3
    MOTION_SENSOR = 4; CONTACT_SENSOR = 5; BUTTON = 6
    OUTLET = 7; SENSOR = 8; GENERIC = 9

class DeviceClass(IntEnum):
    LIGHTING = 0; SHADE = 1; CLIMATE = 2; SECURITY = 3
    CONTROL = 4; SENSOR = 5; OTHER = 6

class DeviceStatus(IntEnum):
    ONLINE = 0; OFFLINE = 1; UNAVAILABLE = 2

class CapabilityType(IntEnum):
    SWITCHING = 0; DIMMING = 1; COLOR_CONTROL = 2
    TEMPERATURE = 3; HUMIDITY = 4; FAN_SPEED = 5
    OPEN_CLOSE = 6; LOCK_UNLOCK = 7; GENERIC = 8

class VdcCapabilityFlag(IntEnum):
    SCENES = 0; SENSOR_EVENTS = 1; OTA_UPDATE = 2
    DYNAMIC_DEVICES = 4; POWER_METERING = 9  # etc.

class MeasurementType(IntEnum):
    TEMPERATURE = 0; HUMIDITY = 1; BRIGHTNESS = 2; CO2 = 3
    POWER = 4; CURRENT = 5; VOLTAGE = 6; ENERGY = 7  # etc.

class EventType(IntEnum):
    STATE_CHANGED = 0; VALUE_REPORTED = 1; TRIGGER = 2

class ErrorCode(IntEnum):
    UNKNOWN = 0; PROTOCOL_ERROR = 1; TIMEOUT = 2
    NOT_SUPPORTED = 3; BAD_REQUEST = 4; AUTH_FAILED = 5
    PERMISSION_DENIED = 6; DEVICE_UNAVAILABLE = 7
    TEMPORARILY_UNAVAILABLE = 8

class Action(IntEnum):
    ACTIVATE = 0; DEACTIVATE = 1
```

---

## 12. Dependencies

```toml
[project]
dependencies = [
    "grpcio>=1.50",
    "grpcio-tools>=1.50",   # dev only, for stub regeneration
    "pyyaml>=6.0",
    "protobuf>=4.0",
]
```

---

## 13. Public API Surface (`__init__.py`)

```python
from pyDSvDCAPIv2 import (
    VDC,
    Device,
    DsUid,
    DeviceType, DeviceClass, DeviceStatus,
    CapabilityType, VdcCapabilityFlag,
    MeasurementType, EventType, Action,
    ErrorCode,
    VDCConnectionError, DeviceError,
)
```

---

## 14. Testing Strategy

- Unit tests for `persistence.py` (load/save/backup/restore)
- Unit tests for `dsuid.py` (deterministic ID generation)
- Unit tests for `enums.py` (value correctness)
- Integration tests using a gRPC mock server (via `grpc.experimental.aio` test utilities)
- Example in `examples/simple_light.py` as a smoke test against a real dSS
