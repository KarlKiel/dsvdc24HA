# pyDSvDCAPIv2 — Design Specification

**Date:** 2026-03-26
**Project:** `pyDSvDCAPIv2` — Python library for the digitalSTROM VDC API v2
**Location:** `C:\Users\I064071\VSC-projects\dsvdc24HA\dsvdc24HA\`

---

## 1. Purpose and Scope

A Python library that implements the digitalSTROM Virtual Device Connector (VDC) API v2, allowing users to easily create a fully working Python-based VDC that manages virtual devices over their complete lifecycle. The library provides:

- A TCP client connecting to the digitalSTROM Server (dSS), sending/receiving length-prefixed protobuf messages
- An optional WebSocket client for real-time event streaming
- Device announcement, update, and removal lifecycle
- Incoming command/state handling via async callbacks
- YAML-based persistence with backup/restore
- Automatic reconnection with full re-announcement
- Periodic heartbeat keepalive

**Not in scope:** The library does not implement a gRPC server or client. The proto files are used only for message serialization.

---

## 2. Protocol Reference

The API v2 specification is at:
`C:\Users\I064071\VSC-projects\vdc2documentation\digitalstrom4HA\vdc_documentation\derivedProtoFiles\`

Key facts:
- **Transport:** Raw protobuf over TCP with 4-byte big-endian length prefix (NOT gRPC over HTTP/2)
- **Connection direction:** VDC connects *to* dSS (default port 62000). dSS is the TCP server, VDC is the TCP client.
- **WebSocket:** Optional secondary channel. After TCP handshake, if VDC announces `ws=1` and `ws-path=/vdc/ws`, the dSS may use a separate WebSocket connection for real-time event push. The VDC also connects to this WebSocket endpoint as a client.
- **Proto files:** Define message structures only. The `service VdcService` block in `vdc_service.proto` is a formal API contract for documentation and code generation — it does NOT imply gRPC runtime usage.
- **Completely incompatible with v1** — v1 uses a custom property-tree protobuf envelope; v2 uses well-typed individual messages with the same length-prefix framing.

### Wire format
```
┌─────────────────────────────────────────┐
│  4 bytes: message length (big-endian)   │
│  N bytes: serialized protobuf message   │
└─────────────────────────────────────────┘
```

### Connection sequence
```
VDC (TCP client)                       dSS (TCP server, port 62000)
 │                                          │
 │──── TCP connect ──────────────────────►  │
 │── ServiceAnnouncement (len-prefixed) ──► │  "I'm vdc-001, version 1.0, caps=[SCENES]"
 │◄── ServiceAcknowledgement ────────────── │  "OK, protocol accepted, session=token"
 │── DeviceAnnouncement ──────────────────► │  "device lamp-001, LIGHT/LIGHTING, ONLINE"
 │── DeviceAnnouncement ──────────────────► │  "device sensor-001, SENSOR/SENSOR, ONLINE"
 │                                          │
 │◄── SetDeviceState ──────────────────────  │  "set lamp-001 brightness=50"
 │── SetStateResponse ────────────────────► │  "OK"
 │◄── SendCommand ─────────────────────────  │  "lamp-001: SWITCH_OFF"
 │── CommandResult ───────────────────────► │  "SUCCESS"
 │                                          │
 │── Heartbeat ───────────────────────────► │  every 30s
 │◄── Heartbeat ───────────────────────────  │  acknowledged
 │                                          │
 │  [optional WebSocket channel]            │
 │──── WS connect to dSS /vdc/ws ────────►  │
 │◄── DeviceEvent stream ──────────────────  │  real-time events pushed by dSS
```

---

## 3. Module Structure

```
pyDSvDCAPIv2/
├── pyDSvDCAPIv2/
│   ├── __init__.py              # Public API: VDC, Device, enums, exceptions
│   ├── vdc.py                   # VDC class — top-level entry point
│   ├── device.py                # Device class — thin wrapper around DeviceAnnouncement
│   ├── dsuid.py                 # dSUID-conformant ID generation (UUID v5, namespaced)
│   ├── connection.py            # TCP connection, length-prefix framing, reconnect loop
│   ├── ws_client.py             # Optional WebSocket event channel
│   ├── heartbeat.py             # Periodic heartbeat asyncio task
│   ├── persistence.py           # YAML load/save with atomic write + .bak backup
│   ├── enums.py                 # Python IntEnums matching proto enum values
│   ├── constants.py             # Known map<string,string> key constants (functional + UI)
│   ├── exceptions.py            # VDCConnectionError, DeviceError
│   └── proto/
│       └── *_pb2.py             # Pre-generated protobuf message classes (committed to repo)
├── examples/
│   └── simple_light.py          # Minimal working example
├── tests/
├── pyproject.toml
└── README.md
```

**Proto files** (`.proto` sources) are excluded from the repo via `.gitignore`. Only the generated `*_pb2.py` message classes are committed. The `_pb2_grpc.py` stub files are NOT generated or used.

---

## 4. VDC Class

The single user-facing entry point.

```python
vdc = VDC(
    vdc_id="my-vdc-001",          # seed for dSUID generation; actual dSUID stored in YAML
    name="My Home Bridge",
    version="1.0.0",
    server_host="192.168.1.10",   # dSS host
    server_port=62000,            # dSS TCP port (default 62000)
    capabilities=[VdcCapabilityFlag.SCENES, VdcCapabilityFlag.DYNAMIC_DEVICES],
    state_path="state.yaml",
    heartbeat_interval=30,        # seconds, default 30
    ws_path="/vdc/ws",            # optional WebSocket path; None to disable
)

vdc.add_device(device)
vdc.remove_device(device_id)     # removes from registry; sends DeviceRemoval if connected

await vdc.start()                 # connect, announce, register devices, start background tasks
await vdc.stop()                  # graceful shutdown
await vdc.flush()                 # force immediate YAML save

# VDC-level incoming callbacks:
vdc.on_scene_event = async_callback    # called when dSS sends SceneActivation
```

On `start()`:
1. Load YAML state (restore resolved vdc_id and device IDs)
2. Open TCP connection to dSS
3. Send `ServiceAnnouncement`, receive `ServiceAcknowledgement` (or raise `VDCConnectionError`)
4. Send `DeviceAnnouncement` for each registered device
5. Start incoming message dispatch loop (background task)
6. Optionally connect WebSocket to dSS event channel
7. Start heartbeat background task

---

## 5. Device Class

Thin wrapper matching the `DeviceAnnouncement` proto exactly.

```python
device = Device(
    device_id="lamp-001",         # seed for dSUID; actual dSUID stored in YAML
    type=DeviceType.LIGHT,
    class_=DeviceClass.LIGHTING,
    name="Kitchen Light",
    status=DeviceStatus.ONLINE,
    capabilities=[VdcCapability(type=CapabilityType.DIMMING, parameters={"minLevel": "0", "maxLevel": "100"})],
    config={"address": "110120301A1A", "model": "dS21-400"},
    attributes={},
    metadata={},
    measurements=[],
    scenes=[],
)

# Incoming callbacks (called by library when dSS sends a message targeting this device):
device.on_set_state = async def(attribute: str, value: str) -> None
device.on_get_state = async def(attribute: str) -> str
device.on_command   = async def(command: str, params: dict) -> dict
device.on_scene     = async def(scene_id: str, action: Action, params: dict) -> None

# Outgoing — update local state and push events to dSS:
await device.update_state("brightness", "75")  # updates local state dict + auto-save
                                                # NOTE: SetStateRequest flows dSS→VDC only;
                                                # VDC pushes unsolicited changes via send_event()
await device.send_event(
    EventType.VALUE_REPORTED,
    attribute="brightness",
    value="75"
)
await device.remove()                           # sends DeviceRemoval, removes from VDC
```

Devices hold a `state: dict[str, str]` — the last-known attribute values. This is persisted to YAML and restored on startup.

---

## 6. dSUID-Conformant ID Generation (`dsuid.py`)

IDs are generated deterministically using UUID v5 (name-based SHA-1) within fixed namespaces, formatted as a 17-byte (34 hex char) dSUID string — matching the digitalSTROM ecosystem convention.

```python
# Fixed namespaces (stable UUID constants):
VDC_NAMESPACE    = UUID("2a4b5d8e-...")
DEVICE_NAMESPACE = UUID("7c1f3a9b-...")

class DsUid:
    @staticmethod
    def for_vdc(seed: str) -> str:
        """Generate stable dSUID for a VDC from a seed string."""

    @staticmethod
    def for_device(seed: str) -> str:
        """Generate stable dSUID for a device from a seed string."""
```

On first `VDC.start()`:
- If `state.yaml` exists and contains a resolved `vdc_id`, reuse it (stable across restarts)
- Otherwise generate from the user-provided seed string, save to YAML

Same logic applies for each `Device.device_id`.

---

## 7. Persistence (`persistence.py`)

**What is persisted:**
- VDC: resolved `vdc_id` (dSUID hex), `name`, `version`, `server_host`, `server_port`, `capabilities`
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
  - device_id: "0201020304050607080910111213141516"
    type: 0
    class_: 0
    name: "Kitchen Light"
    status: 0
    config:
      address: "110120301A1A"
      model: "dS21-400"
    capabilities:
      - type: 1
        parameters:
          minLevel: "0"
          maxLevel: "100"
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

Owns the TCP connection and length-prefix framing. Implements reconnect loop.

**Message framing:**
- Send: serialize protobuf → prepend 4-byte big-endian length → write to socket
- Receive: read 4-byte length → read exactly that many bytes → deserialize protobuf

**Incoming message dispatch:**
- Single asyncio read loop receives all messages from dSS
- Dispatches by message type to the appropriate device callback or VDC-level handler:
  - `SetStateRequest` → find device by `deviceId` → call `device.on_set_state`
  - `StateRequest` → find device by `deviceId` → call `device.on_get_state`
  - `Command` → find device by `deviceId` → call `device.on_command`
  - `SceneActivation` → call `vdc.on_scene_event`
  - `FirmwareUpdateRequest` → find device → call `device.on_firmware_update` (if set)
  - `Heartbeat` → echo back immediately

**Reconnect strategy:** exponential backoff starting at 2s, doubling each attempt, capped at 60s.

**On disconnect/error:**
1. Cancel all background tasks (heartbeat, WS client)
2. Wait backoff delay
3. Re-open TCP connection
4. Re-run full announce + device registration sequence
5. Restart background tasks

---

## 9. WebSocket Event Channel (`ws_client.py`)

Optional secondary channel. Activated if `ws_path` is set on `VDC` and dSS accepts it
(i.e. `ServiceAcknowledgement.options["upgrade"] == "websocket"`).

- VDC connects as WebSocket client to `ws://{server_host}:{server_port}{ws_path}`
- Receives `DeviceEvent` messages pushed by dSS
- Dispatches to `device.on_set_state` / `device.on_command` etc. same as TCP channel
- Auto-reconnects independently if WebSocket drops

---

## 10. Heartbeat (`heartbeat.py`)

Simple asyncio loop:
```python
while running:
    send(Heartbeat(vdc_id=vdc_id, timestamp=now_ms(), metrics=vdc.heartbeat_metrics))
    await asyncio.sleep(interval)
```

Optional `metrics` map populated by the user via `vdc.heartbeat_metrics: dict[str, str]`.

---

## 11. Error Handling

- `VDCConnectionError` — raised from `start()` if handshake fails (e.g. `ServiceAcknowledgement` contains error)
- `DeviceError` — raised if `SetStateResponse` or `CommandResult` returns non-OK status
- TCP/socket errors → logged + trigger reconnect loop (never propagated to user)
- User callback exceptions → logged, do not crash the VDC

---

## 12. Enums (`enums.py`)

Python `IntEnum` classes matching proto enum values exactly, so users never import from `_pb2` directly:

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
    SCENES = 0; SENSOR_EVENTS = 1; OTA_UPDATE = 2; ADVANCED_ERROR = 3
    DYNAMIC_DEVICES = 4; CUSTOM_METADATA = 5; MULTI_USER = 6
    LOCALIZATION = 7; SECURE_AUTH = 8; POWER_METERING = 9
    INTERLOCK = 10; TIMERS = 11; REMOVABLE = 12; ALERTS = 13
    FIRMWARE_VERSIONING = 14; SCENE_TRANSITIONS = 15
    PROTOCOL_VERSIONS = 16; BATCH_COMMANDS = 17; STATISTICS = 18

class MeasurementType(IntEnum):
    TEMPERATURE = 0; HUMIDITY = 1; BRIGHTNESS = 2; CO2 = 3
    POWER = 4; CURRENT = 5; VOLTAGE = 6; ENERGY = 7
    FREQUENCY = 8; PRESSURE = 9; WINDSPEED = 10; WINDDIRECTION = 11
    RAIN = 12; UV_INDEX = 13; ILLUMINANCE = 14; GENERIC = 15

class EventType(IntEnum):
    STATE_CHANGED = 0; VALUE_REPORTED = 1; TRIGGER = 2

class ErrorCode(IntEnum):
    UNKNOWN = 0; PROTOCOL_ERROR = 1; TIMEOUT = 2
    NOT_SUPPORTED = 3; BAD_REQUEST = 4; AUTH_FAILED = 5
    PERMISSION_DENIED = 6; DEVICE_UNAVAILABLE = 7; TEMPORARILY_UNAVAILABLE = 8

class Action(IntEnum):
    ACTIVATE = 0; DEACTIVATE = 1

class CommandStatus(IntEnum):
    OK = 0; FAILED = 1; QUEUED = 2

class SceneType(IntEnum):
    GENERAL = 0; AWAY = 1; NIGHT = 2; VACATION = 3; CUSTOM = 4
```

---

## 13. Known Key-Value Constants (`constants.py`)

A `constants.py` module provides string constants for all known `map<string,string>` keys used
in the protocol. Prevents magic string typos and enables IDE autocomplete. Includes both
FUNCTIONAL keys (affect dSS behavior) and UI-ONLY keys (affect dSS dashboard rendering).

```python
class ServiceConfig:
    """Keys for ServiceAnnouncement.config (VDC → dSS). FUNCTIONAL."""
    PROTO   = "proto"      # "protobuf" — encoding declaration
    WS      = "ws"         # "1" to enable WebSocket event channel
    WS_PATH = "ws-path"    # e.g. "/vdc/ws" — WebSocket endpoint path
    # UI ONLY (diagnostic display in dSS admin):
    ENDPOINT = "endpoint"  # e.g. "/vdc"
    SECURE   = "secure"    # "1" if TLS
    HOST     = "host"      # VDC hostname/IP for display
    PORT     = "port"      # VDC port for display

class AckOptions:
    """Keys for ServiceAcknowledgement.options (dSS → VDC). FUNCTIONAL."""
    SESSION   = "session"    # opaque reconnect token
    UPGRADE   = "upgrade"    # "websocket" — event channel upgrade accepted
    RECONNECT = "reconnect"  # "true"/"false"
    EXPIRES   = "expires"    # session TTL in seconds (as string)

class ServiceEndpoints:
    """Keys for ServiceAnnouncement.endpoints (dSS → VDC)."""
    API = "api"   # FUNCTIONAL — VDC REST endpoint root path
    WEB = "web"   # UI ONLY — dashboard URL
    OTA = "ota"   # UI ONLY — firmware update endpoint

class DeviceConfig:
    """Keys for DeviceAnnouncement.config / DeviceUpdate.config (VDC → dSS)."""
    # FUNCTIONAL:
    ADDRESS  = "address"   # digitalSTROM dSID hex string (device registration)
    MODEL    = "model"     # device model identifier (device-type filter)
    TOKEN    = "token"     # opaque token for secure onboarding
    # UI ONLY:
    SERIAL           = "serial"           # device serial number
    FIRMWARE_VERSION = "firmwareVersion"  # e.g. "2.3.1"
    MANUFACTURER     = "manufacturer"     # e.g. "digitalSTROM AG"
    MAC              = "mac"              # e.g. "AA:BB:CC:11:22:33"
    INSTALLATION_CODE = "installationCode"

class DeviceMetadata:
    """Keys for DeviceAnnouncement.metadata / DeviceUpdate.metadata. UI ONLY."""
    ICON                 = "icon"                 # icon path/URL (svg/png)
    INSTALL_DATE         = "installDate"          # ISO date e.g. "2023-10-11"
    LOCATION_DESCRIPTION = "locationDescription"  # e.g. "Attic / West corner"
    WARRANTY_UNTIL       = "warrantyUntil"        # ISO date
    ASSET_ID             = "assetId"              # asset management ID

class DeviceAttributes:
    """Keys for DeviceAnnouncement.attributes / DeviceUpdate.attributes. UI ONLY.
    These place the device correctly in the dSS room/floor/group structure,
    making virtual devices appear native in the dSS UI."""
    ROOM    = "room"     # must match room name in dSS structure/area
    FLOOR   = "floor"    # must match floor/area name in dSS
    GROUP   = "group"    # scene/grouping label e.g. "Chandeliers"
    SUBTYPE = "subtype"  # controls UI icon/badge:
                         # "RGB", "RGBW", "sensor", "dimmer", "HVAC", "generic"

class DimmingParams:
    """Keys for VdcCapability.parameters where type=DIMMING. FUNCTIONAL."""
    MIN_LEVEL = "minLevel"   # integer 0-100 as string
    MAX_LEVEL = "maxLevel"   # integer 0-100 as string

class ColorParams:
    """Keys for VdcCapability.parameters where type=COLOR_CONTROL."""
    # UI ONLY — controls color picker rendering in dSS UI:
    SUPPORTED_COLORS = "supportedColors"  # comma-separated: "red,green,blue,white,..."
    COLOR_MODE       = "colorMode"        # "RGB", "RGBW", "CCT", "HSV", "DIM"

class CommandParams:
    """Keys for Command.parameters (dSS → VDC). FUNCTIONAL."""
    COLOR    = "color"    # HTML hex e.g. "#A4B234" — for SET_COLOR
    LEVEL    = "level"    # 0-100 string — for SET_BRIGHTNESS
    SETPOINT = "setpoint" # float Celsius string — for SET_TEMPERATURE
    SCENE_ID = "sceneId"  # valid sceneId string — for SET_SCENE

class CommandResultKeys:
    """Keys for CommandResult.result (VDC → dSS). FUNCTIONAL."""
    STATUS  = "status"   # "ok", "rejected", "error", "partial"
    INFO    = "info"     # UI ONLY — human-readable explanation
    APPLIED = "applied"  # "true"/"false" — whether command was carried out

class SceneAttributes:
    """Keys for Scene.attributes. UI ONLY — affect scene badge rendering in dSS UI."""
    USAGE_HINT = "usageHint"  # "Party", "Relax", "Reading", "Night", "AllOn", etc.
    MOOD_COLOR = "moodColor"  # HTML hex e.g. "#FFD700" — scene tile background color
```

All constants are grouped by message and field, with inline comments indicating whether
each key is FUNCTIONAL (must be correct) or UI ONLY (affects dSS dashboard rendering).

---

## 14. Dependencies

```toml
[project]
dependencies = [
    "protobuf>=4.0",
    "pyyaml>=6.0",
    "websockets>=11.0",
    "zeroconf>=0.80.0",    # optional: for mDNS-based dSS discovery
]
```

No `grpcio` dependency. Proto stubs generated with `protoc --python_out` only (no `--grpc_out`).

---

## 14. Public API Surface (`__init__.py`)

```python
from pyDSvDCAPIv2 import (
    VDC,
    Device,
    VdcCapability,
    DsUid,
    DeviceType, DeviceClass, DeviceStatus,
    CapabilityType, VdcCapabilityFlag,
    MeasurementType, EventType, Action,
    CommandStatus, SceneType, ErrorCode,
    VDCConnectionError, DeviceError,
    # Key-value constants:
    ServiceConfig, AckOptions, ServiceEndpoints,
    DeviceConfig, DeviceMetadata, DeviceAttributes,
    DimmingParams, ColorParams, CommandParams,
    CommandResultKeys, SceneAttributes,
)
```

---

## 15. Testing Strategy

- Unit tests for `persistence.py` (load/save/backup/restore/atomic write)
- Unit tests for `dsuid.py` (deterministic, stable ID generation)
- Unit tests for `connection.py` (length-prefix framing, message dispatch)
- Integration tests using a mock TCP server that speaks the length-prefix protocol
- Example in `examples/simple_light.py` as a smoke test against a real dSS
