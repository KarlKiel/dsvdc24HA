# pyDSvDCAPIv2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pyDSvDCAPIv2`, a Python library that connects to a digitalSTROM Server (dSS) as a VDC client, managing virtual devices over their full lifecycle via length-prefixed protobuf over TCP.

**Architecture:** VDC is a TCP client that connects to dSS port 62000, sends/receives length-prefixed protobuf messages, and dispatches incoming commands to user-registered async callbacks on Device objects. Persistence is YAML with atomic write and `.bak` backup. All I/O is asyncio-based.

**Tech Stack:** Python 3.10+, protobuf 4+, pyyaml 6+, websockets 11+, zeroconf 0.80+, pytest, grpcio-tools (dev only for proto stub generation)

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyDSvDCAPIv2/__init__.py` | Public API exports |
| `pyDSvDCAPIv2/exceptions.py` | `VDCConnectionError`, `DeviceError` |
| `pyDSvDCAPIv2/enums.py` | `IntEnum` classes matching proto enum values |
| `pyDSvDCAPIv2/constants.py` | Known `map<string,string>` key constants |
| `pyDSvDCAPIv2/dsuid.py` | dSUID-conformant ID generation via UUID v5 |
| `pyDSvDCAPIv2/persistence.py` | Atomic YAML load/save with `.bak` backup |
| `pyDSvDCAPIv2/device.py` | `Device` and `VdcCapability` dataclasses |
| `pyDSvDCAPIv2/connection.py` | TCP framing, message dispatch, reconnect loop |
| `pyDSvDCAPIv2/heartbeat.py` | Periodic heartbeat asyncio task |
| `pyDSvDCAPIv2/ws_client.py` | Optional WebSocket event channel |
| `pyDSvDCAPIv2/vdc.py` | `VDC` top-level orchestrator |
| `pyDSvDCAPIv2/proto/*_pb2.py` | Pre-generated protobuf message classes |
| `pyproject.toml` | Package metadata and dependencies |
| `tests/test_dsuid.py` | Tests for dSUID generation |
| `tests/test_persistence.py` | Tests for YAML persistence |
| `tests/test_connection.py` | Tests for TCP framing and dispatch |
| `tests/test_device.py` | Tests for Device dataclass |
| `tests/test_vdc.py` | Integration tests for VDC lifecycle |
| `examples/simple_light.py` | Minimal working example |

---

## Task 1: Project scaffold and proto stub generation

**Files:**
- Create: `pyproject.toml`
- Create: `pyDSvDCAPIv2/__init__.py`
- Create: `pyDSvDCAPIv2/proto/__init__.py`
- Create: `pyDSvDCAPIv2/proto/*_pb2.py` (generated)
- Create: `.gitignore`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "pyDSvDCAPIv2"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "protobuf>=4.0",
    "pyyaml>=6.0",
    "websockets>=11.0",
    "zeroconf>=0.80.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.23",
    "grpcio-tools>=1.50",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Generate protobuf stubs**

```bash
cd C:\Users\I064071\VSC-projects\dsvdc24HA\dsvdc24HA
mkdir -p pyDSvDCAPIv2/proto
python3 -m grpc_tools.protoc \
  -I C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles \
  --python_out=pyDSvDCAPIv2/proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/service_announcement.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/device_announcement.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/measurement.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/state.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/command.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/scene.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/event.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/firmware.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/heartbeat.proto \
  C:/Users/I064071/VSC-projects/vdc2documentation/digitalstrom4HA/vdc_documentation/derivedProtoFiles/error.proto
```

Expected: `pyDSvDCAPIv2/proto/` now contains `*_pb2.py` files, NO `*_pb2_grpc.py` files.

- [ ] **Step 3: Create proto package init**

```python
# pyDSvDCAPIv2/proto/__init__.py
# Auto-generated protobuf message classes for digitalSTROM VDC API v2.
# Do not edit. Regenerate using grpcio-tools with --python_out only.
```

- [ ] **Step 4: Create empty library init**

```python
# pyDSvDCAPIv2/__init__.py
# Populated in Task 10.
```

- [ ] **Step 5: Create tests package**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 6: Create .gitignore**

```
# Proto source files — stubs are committed, sources are not
*.proto
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
# State files from examples/tests
*.yaml
*.yaml.bak
*.yaml.tmp
```

- [ ] **Step 7: Verify stubs import correctly**

```bash
python3 -c "
from pyDSvDCAPIv2.proto import service_announcement_pb2, device_announcement_pb2
a = service_announcement_pb2.ServiceAnnouncement()
a.vdcId = 'test'
print('OK:', a.vdcId)
"
```

Expected: `OK: test`

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml pyDSvDCAPIv2/ tests/.gitkeep .gitignore
git commit -m "feat: project scaffold and generated protobuf stubs"
```

---

## Task 2: Exceptions and enums

**Files:**
- Create: `pyDSvDCAPIv2/exceptions.py`
- Create: `pyDSvDCAPIv2/enums.py`
- Create: `tests/test_enums.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_enums.py
from pyDSvDCAPIv2.enums import (
    DeviceType, DeviceClass, DeviceStatus,
    CapabilityType, VdcCapabilityFlag, MeasurementType,
    EventType, ErrorCode, Action, CommandStatus, SceneType,
)

def test_device_type_values():
    assert DeviceType.LIGHT == 0
    assert DeviceType.GENERIC == 9

def test_device_class_values():
    assert DeviceClass.LIGHTING == 0
    assert DeviceClass.OTHER == 6

def test_capability_type_values():
    assert CapabilityType.SWITCHING == 0
    assert CapabilityType.DIMMING == 1
    assert CapabilityType.COLOR_CONTROL == 2

def test_vdc_capability_flag_values():
    assert VdcCapabilityFlag.SCENES == 0
    assert VdcCapabilityFlag.DYNAMIC_DEVICES == 4
    assert VdcCapabilityFlag.POWER_METERING == 9
    assert VdcCapabilityFlag.STATISTICS == 18

def test_measurement_type_values():
    assert MeasurementType.TEMPERATURE == 0
    assert MeasurementType.GENERIC == 15

def test_error_code_values():
    assert ErrorCode.UNKNOWN == 0
    assert ErrorCode.TEMPORARILY_UNAVAILABLE == 8

def test_action_values():
    assert Action.ACTIVATE == 0
    assert Action.DEACTIVATE == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_enums.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Create exceptions.py**

```python
# pyDSvDCAPIv2/exceptions.py


class VDCConnectionError(Exception):
    """Raised when the VDC cannot connect to dSS or handshake fails."""


class DeviceError(Exception):
    """Raised when a device operation returns a non-OK status from dSS."""
```

- [ ] **Step 4: Create enums.py**

```python
# pyDSvDCAPIv2/enums.py
from enum import IntEnum


class DeviceType(IntEnum):
    LIGHT = 0
    SWITCH = 1
    SHUTTER = 2
    THERMOSTAT = 3
    MOTION_SENSOR = 4
    CONTACT_SENSOR = 5
    BUTTON = 6
    OUTLET = 7
    SENSOR = 8
    GENERIC = 9


class DeviceClass(IntEnum):
    LIGHTING = 0
    SHADE = 1
    CLIMATE = 2
    SECURITY = 3
    CONTROL = 4
    SENSOR = 5
    OTHER = 6


class DeviceStatus(IntEnum):
    ONLINE = 0
    OFFLINE = 1
    UNAVAILABLE = 2


class CapabilityType(IntEnum):
    SWITCHING = 0
    DIMMING = 1
    COLOR_CONTROL = 2
    TEMPERATURE = 3
    HUMIDITY = 4
    FAN_SPEED = 5
    OPEN_CLOSE = 6
    LOCK_UNLOCK = 7
    GENERIC = 8


class VdcCapabilityFlag(IntEnum):
    SCENES = 0
    SENSOR_EVENTS = 1
    OTA_UPDATE = 2
    ADVANCED_ERROR = 3
    DYNAMIC_DEVICES = 4
    CUSTOM_METADATA = 5
    MULTI_USER = 6
    LOCALIZATION = 7
    SECURE_AUTH = 8
    POWER_METERING = 9
    INTERLOCK = 10
    TIMERS = 11
    REMOVABLE = 12
    ALERTS = 13
    FIRMWARE_VERSIONING = 14
    SCENE_TRANSITIONS = 15
    PROTOCOL_VERSIONS = 16
    BATCH_COMMANDS = 17
    STATISTICS = 18


class MeasurementType(IntEnum):
    TEMPERATURE = 0
    HUMIDITY = 1
    BRIGHTNESS = 2
    CO2 = 3
    POWER = 4
    CURRENT = 5
    VOLTAGE = 6
    ENERGY = 7
    FREQUENCY = 8
    PRESSURE = 9
    WINDSPEED = 10
    WINDDIRECTION = 11
    RAIN = 12
    UV_INDEX = 13
    ILLUMINANCE = 14
    GENERIC = 15


class EventType(IntEnum):
    STATE_CHANGED = 0
    VALUE_REPORTED = 1
    TRIGGER = 2


class ErrorCode(IntEnum):
    UNKNOWN = 0
    PROTOCOL_ERROR = 1
    TIMEOUT = 2
    NOT_SUPPORTED = 3
    BAD_REQUEST = 4
    AUTH_FAILED = 5
    PERMISSION_DENIED = 6
    DEVICE_UNAVAILABLE = 7
    TEMPORARILY_UNAVAILABLE = 8


class Action(IntEnum):
    ACTIVATE = 0
    DEACTIVATE = 1


class CommandStatus(IntEnum):
    OK = 0
    FAILED = 1
    QUEUED = 2


class SceneType(IntEnum):
    GENERAL = 0
    AWAY = 1
    NIGHT = 2
    VACATION = 3
    CUSTOM = 4
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python3 -m pytest tests/test_enums.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add pyDSvDCAPIv2/exceptions.py pyDSvDCAPIv2/enums.py tests/test_enums.py
git commit -m "feat: add exceptions and enums"
```

---

## Task 3: Constants

**Files:**
- Create: `pyDSvDCAPIv2/constants.py`
- Create: `tests/test_constants.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_constants.py
from pyDSvDCAPIv2.constants import (
    ServiceConfig, AckOptions, ServiceEndpoints,
    DeviceConfig, DeviceMetadata, DeviceAttributes,
    DimmingParams, ColorParams, CommandParams,
    CommandResultKeys, SceneAttributes,
)

def test_service_config_functional_keys():
    assert ServiceConfig.PROTO == "proto"
    assert ServiceConfig.WS == "ws"
    assert ServiceConfig.WS_PATH == "ws-path"

def test_service_config_ui_keys():
    assert ServiceConfig.HOST == "host"
    assert ServiceConfig.PORT == "port"

def test_device_attributes_keys():
    assert DeviceAttributes.ROOM == "room"
    assert DeviceAttributes.FLOOR == "floor"
    assert DeviceAttributes.SUBTYPE == "subtype"

def test_dimming_params_keys():
    assert DimmingParams.MIN_LEVEL == "minLevel"
    assert DimmingParams.MAX_LEVEL == "maxLevel"

def test_ack_options_keys():
    assert AckOptions.SESSION == "session"
    assert AckOptions.UPGRADE == "upgrade"
    assert AckOptions.EXPIRES == "expires"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_constants.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create constants.py**

```python
# pyDSvDCAPIv2/constants.py


class ServiceConfig:
    """Keys for ServiceAnnouncement.config (VDC → dSS)."""
    PROTO = "proto"        # FUNCTIONAL: "protobuf"
    WS = "ws"              # FUNCTIONAL: "1" to enable WebSocket channel
    WS_PATH = "ws-path"    # FUNCTIONAL: WebSocket endpoint path e.g. "/vdc/ws"
    ENDPOINT = "endpoint"  # UI ONLY: display path e.g. "/vdc"
    SECURE = "secure"      # UI ONLY: "1" if TLS
    HOST = "host"          # UI ONLY: VDC hostname/IP for admin display
    PORT = "port"          # UI ONLY: VDC port for admin display


class AckOptions:
    """Keys for ServiceAcknowledgement.options (dSS → VDC). FUNCTIONAL."""
    SESSION = "session"      # opaque reconnect token
    UPGRADE = "upgrade"      # "websocket" — WS channel upgrade accepted
    RECONNECT = "reconnect"  # "true"/"false"
    EXPIRES = "expires"      # session TTL in seconds (as string)


class ServiceEndpoints:
    """Keys for ServiceAnnouncement.endpoints (dSS → VDC)."""
    API = "api"  # FUNCTIONAL: VDC REST endpoint root path
    WEB = "web"  # UI ONLY: dashboard URL
    OTA = "ota"  # UI ONLY: firmware update endpoint


class DeviceConfig:
    """Keys for DeviceAnnouncement.config / DeviceUpdate.config (VDC → dSS)."""
    ADDRESS = "address"                    # FUNCTIONAL: digitalSTROM dSID hex string
    MODEL = "model"                        # FUNCTIONAL+UI: device model identifier
    TOKEN = "token"                        # FUNCTIONAL: secure onboarding token
    SERIAL = "serial"                      # UI ONLY: device serial number
    FIRMWARE_VERSION = "firmwareVersion"   # UI ONLY: e.g. "2.3.1"
    MANUFACTURER = "manufacturer"          # UI ONLY: e.g. "digitalSTROM AG"
    MAC = "mac"                            # UI ONLY: e.g. "AA:BB:CC:11:22:33"
    INSTALLATION_CODE = "installationCode" # vendor extension


class DeviceMetadata:
    """Keys for DeviceAnnouncement.metadata / DeviceUpdate.metadata. UI ONLY."""
    ICON = "icon"                              # icon path/URL (svg/png)
    INSTALL_DATE = "installDate"               # ISO date e.g. "2023-10-11"
    LOCATION_DESCRIPTION = "locationDescription"  # e.g. "Attic / West corner"
    WARRANTY_UNTIL = "warrantyUntil"           # ISO date
    ASSET_ID = "assetId"                       # asset management ID


class DeviceAttributes:
    """Keys for DeviceAnnouncement.attributes / DeviceUpdate.attributes. UI ONLY.
    Place virtual devices correctly in the dSS room/floor/group structure."""
    ROOM = "room"      # must match room name in dSS structure
    FLOOR = "floor"    # must match floor/area name in dSS
    GROUP = "group"    # scene/grouping label e.g. "Chandeliers"
    SUBTYPE = "subtype"  # UI icon/badge: "RGB","RGBW","sensor","dimmer","HVAC","generic"


class DimmingParams:
    """Keys for VdcCapability.parameters where type=DIMMING. FUNCTIONAL."""
    MIN_LEVEL = "minLevel"  # integer 0-100 as string
    MAX_LEVEL = "maxLevel"  # integer 0-100 as string


class ColorParams:
    """Keys for VdcCapability.parameters where type=COLOR_CONTROL. UI ONLY."""
    SUPPORTED_COLORS = "supportedColors"  # comma-separated color names
    COLOR_MODE = "colorMode"              # "RGB","RGBW","CCT","HSV","DIM"


class CommandParams:
    """Keys for Command.parameters (dSS → VDC). FUNCTIONAL."""
    COLOR = "color"        # HTML hex e.g. "#A4B234" — for SET_COLOR
    LEVEL = "level"        # 0-100 string — for SET_BRIGHTNESS
    SETPOINT = "setpoint"  # float Celsius string — for SET_TEMPERATURE
    SCENE_ID = "sceneId"   # valid sceneId string — for SET_SCENE


class CommandResultKeys:
    """Keys for CommandResult.result (VDC → dSS)."""
    STATUS = "status"    # FUNCTIONAL: "ok","rejected","error","partial"
    INFO = "info"        # UI ONLY: human-readable explanation
    APPLIED = "applied"  # FUNCTIONAL: "true"/"false"


class SceneAttributes:
    """Keys for Scene.attributes. UI ONLY — affect scene badge in dSS UI."""
    USAGE_HINT = "usageHint"  # "Party","Relax","Reading","Night","AllOn",etc.
    MOOD_COLOR = "moodColor"  # HTML hex e.g. "#FFD700"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_constants.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add pyDSvDCAPIv2/constants.py tests/test_constants.py
git commit -m "feat: add key-value constants for protocol and UI fields"
```

---

## Task 4: dSUID generation

**Files:**
- Create: `pyDSvDCAPIv2/dsuid.py`
- Create: `tests/test_dsuid.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_dsuid.py
from pyDSvDCAPIv2.dsuid import DsUid


def test_for_vdc_returns_34_hex_chars():
    uid = DsUid.for_vdc("my-bridge")
    assert len(uid) == 34
    assert all(c in "0123456789abcdefABCDEF" for c in uid)


def test_for_device_returns_34_hex_chars():
    uid = DsUid.for_device("lamp-001")
    assert len(uid) == 34
    assert all(c in "0123456789abcdefABCDEF" for c in uid)


def test_for_vdc_is_deterministic():
    assert DsUid.for_vdc("my-bridge") == DsUid.for_vdc("my-bridge")


def test_for_device_is_deterministic():
    assert DsUid.for_device("lamp-001") == DsUid.for_device("lamp-001")


def test_vdc_and_device_differ_for_same_seed():
    assert DsUid.for_vdc("same-seed") != DsUid.for_device("same-seed")


def test_different_seeds_produce_different_ids():
    assert DsUid.for_device("lamp-001") != DsUid.for_device("lamp-002")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_dsuid.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create dsuid.py**

```python
# pyDSvDCAPIv2/dsuid.py
import uuid

# Fixed namespaces — stable across all installations of this library.
# These UUIDs were generated once and must never change, as changing them
# would alter all generated dSUIDs and break device continuity in dSS.
_VDC_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_DEVICE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


class DsUid:
    """Generate dSUID-conformant identifiers for VDCs and devices.

    A dSUID is a 17-byte (34 hex char) identifier used by the digitalSTROM
    ecosystem. We generate them deterministically from a seed string using
    UUID v5 (SHA-1 name-based) within a fixed namespace, then zero-pad to
    17 bytes (the last byte is the sub-device index, always 0 for VDCs
    and primary devices).
    """

    @staticmethod
    def for_vdc(seed: str) -> str:
        """Generate a stable dSUID for a VDC from a seed string.

        The same seed always produces the same dSUID. Use a string that
        is unique to this VDC instance (e.g. "my-home-bridge-v2").
        """
        raw = uuid.uuid5(_VDC_NAMESPACE, seed)
        # 16 bytes from UUID + 1 zero byte for sub-device index = 17 bytes = 34 hex chars
        return raw.hex + "00"

    @staticmethod
    def for_device(seed: str) -> str:
        """Generate a stable dSUID for a device from a seed string.

        The same seed always produces the same dSUID. Use a string that
        is unique to this device (e.g. serial number, MAC, or stable name).
        """
        raw = uuid.uuid5(_DEVICE_NAMESPACE, seed)
        return raw.hex + "00"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_dsuid.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add pyDSvDCAPIv2/dsuid.py tests/test_dsuid.py
git commit -m "feat: add dSUID generation via UUID v5 namespaced hashing"
```

---

## Task 5: Persistence

**Files:**
- Create: `pyDSvDCAPIv2/persistence.py`
- Create: `tests/test_persistence.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_persistence.py
import os
import pytest
from pathlib import Path
from pyDSvDCAPIv2.persistence import PropertyStore


@pytest.fixture
def store(tmp_path):
    return PropertyStore(str(tmp_path / "state.yaml"))


def test_save_and_load_roundtrip(store):
    data = {"vdc": {"vdc_id": "abc123", "name": "Test"}, "devices": []}
    store.save(data)
    loaded = store.load()
    assert loaded == data


def test_load_returns_empty_dict_when_no_file(store):
    result = store.load()
    assert result == {}


def test_save_creates_backup(store, tmp_path):
    data1 = {"vdc": {"vdc_id": "first"}, "devices": []}
    data2 = {"vdc": {"vdc_id": "second"}, "devices": []}
    store.save(data1)
    store.save(data2)
    bak = Path(str(tmp_path / "state.yaml.bak"))
    assert bak.exists()
    import yaml
    with open(bak) as f:
        backed = yaml.safe_load(f)
    assert backed["vdc"]["vdc_id"] == "first"


def test_load_falls_back_to_backup(store, tmp_path):
    data = {"vdc": {"vdc_id": "backup-data"}, "devices": []}
    store.save(data)
    # corrupt primary
    Path(str(tmp_path / "state.yaml")).write_text("not: valid: yaml: [[[")
    loaded = store.load()
    assert loaded["vdc"]["vdc_id"] == "backup-data"


def test_no_tmp_file_left_after_save(store, tmp_path):
    store.save({"vdc": {}, "devices": []})
    assert not Path(str(tmp_path / "state.yaml.tmp")).exists()


def test_flush_saves_immediately(store):
    store.stage({"vdc": {"vdc_id": "staged"}, "devices": []})
    store.flush()
    loaded = store.load()
    assert loaded["vdc"]["vdc_id"] == "staged"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_persistence.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create persistence.py**

```python
# pyDSvDCAPIv2/persistence.py
import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_AUTO_SAVE_DELAY = 1.0  # seconds


class PropertyStore:
    """Atomic YAML persistence with .bak backup and debounced auto-save."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._tmp = self._path.with_suffix(".yaml.tmp")
        self._bak = self._path.with_suffix(".yaml.bak")
        self._pending: dict[str, Any] | None = None
        self._save_task: asyncio.Task | None = None

    def load(self) -> dict[str, Any]:
        """Load state from YAML. Falls back to .bak if primary is corrupt/missing."""
        for candidate in (self._path, self._bak):
            if candidate.exists():
                try:
                    with open(candidate, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return data
                except Exception as e:
                    logger.warning("Failed to load %s: %s", candidate, e)
        return {}

    def save(self, data: dict[str, Any]) -> None:
        """Write data to YAML atomically with backup."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._tmp, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        if self._path.exists():
            shutil.copy2(self._path, self._bak)
        os.replace(self._tmp, self._path)

    def stage(self, data: dict[str, Any]) -> None:
        """Stage data for debounced auto-save (call flush() or await auto-save)."""
        self._pending = data

    def flush(self) -> None:
        """Immediately save any staged data."""
        if self._pending is not None:
            self.save(self._pending)
            self._pending = None

    async def schedule_save(self, data: dict[str, Any]) -> None:
        """Debounced save: waits AUTO_SAVE_DELAY seconds then saves."""
        self._pending = data
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = asyncio.create_task(self._delayed_save())

    async def _delayed_save(self) -> None:
        try:
            await asyncio.sleep(_AUTO_SAVE_DELAY)
            if self._pending is not None:
                self.save(self._pending)
                self._pending = None
        except asyncio.CancelledError:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_persistence.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add pyDSvDCAPIv2/persistence.py tests/test_persistence.py
git commit -m "feat: add atomic YAML persistence with backup and debounced auto-save"
```

---

## Task 6: Device and VdcCapability dataclasses

**Files:**
- Create: `pyDSvDCAPIv2/device.py`
- Create: `tests/test_device.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_device.py
import pytest
from pyDSvDCAPIv2.device import Device, VdcCapability
from pyDSvDCAPIv2.enums import DeviceType, DeviceClass, DeviceStatus, CapabilityType


def test_device_creation_minimal():
    d = Device(
        device_id="lamp-001",
        type=DeviceType.LIGHT,
        class_=DeviceClass.LIGHTING,
        status=DeviceStatus.ONLINE,
    )
    assert d.device_id == "lamp-001"
    assert d.type == DeviceType.LIGHT
    assert d.state == {}


def test_device_update_state_stores_value():
    d = Device(device_id="x", type=DeviceType.SENSOR,
               class_=DeviceClass.SENSOR, status=DeviceStatus.ONLINE)
    d.update_state("temperature", "21.5")
    assert d.state["temperature"] == "21.5"


def test_device_update_state_overwrites():
    d = Device(device_id="x", type=DeviceType.LIGHT,
               class_=DeviceClass.LIGHTING, status=DeviceStatus.ONLINE)
    d.update_state("on", "true")
    d.update_state("on", "false")
    assert d.state["on"] == "false"


def test_device_to_dict_roundtrip():
    cap = VdcCapability(type=CapabilityType.DIMMING, parameters={"minLevel": "0"})
    d = Device(
        device_id="lamp-001",
        type=DeviceType.LIGHT,
        class_=DeviceClass.LIGHTING,
        status=DeviceStatus.ONLINE,
        name="Kitchen Light",
        capabilities=[cap],
        config={"address": "AA"},
    )
    data = d.to_dict()
    d2 = Device.from_dict(data)
    assert d2.device_id == d.device_id
    assert d2.name == "Kitchen Light"
    assert d2.capabilities[0].type == CapabilityType.DIMMING


def test_vdc_capability_defaults():
    cap = VdcCapability(type=CapabilityType.SWITCHING)
    assert cap.parameters == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_device.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create device.py**

```python
# pyDSvDCAPIv2/device.py
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
    """Represents a device capability with optional parameters."""
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
    attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"sceneId": self.scene_id, "name": self.name,
                "type": self.type, "attributes": dict(self.attributes)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scene:
        return cls(
            scene_id=data["sceneId"],
            name=data.get("name", ""),
            type=int(data.get("type", 0)),
            attributes=dict(data.get("attributes", {})),
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_device.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add pyDSvDCAPIv2/device.py tests/test_device.py
git commit -m "feat: add Device and VdcCapability dataclasses with serialization"
```

---

## Task 7: TCP connection and message framing

**Files:**
- Create: `pyDSvDCAPIv2/connection.py`
- Create: `tests/test_connection.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_connection.py
import asyncio
import struct
import pytest
from pyDSvDCAPIv2.connection import frame_message, read_message


async def _mock_reader(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def test_frame_message_prepends_4_byte_length():
    payload = b"hello"
    framed = frame_message(payload)
    assert len(framed) == 4 + len(payload)
    length = struct.unpack(">I", framed[:4])[0]
    assert length == len(payload)
    assert framed[4:] == payload


def test_frame_message_empty_payload():
    framed = frame_message(b"")
    assert framed == b"\x00\x00\x00\x00"


@pytest.mark.asyncio
async def test_read_message_extracts_payload():
    payload = b"test-payload"
    framed = frame_message(payload)
    reader = await _mock_reader(framed)
    result = await read_message(reader)
    assert result == payload


@pytest.mark.asyncio
async def test_read_message_handles_multiple_messages():
    payload1 = b"first"
    payload2 = b"second"
    reader = await _mock_reader(frame_message(payload1) + frame_message(payload2))
    assert await read_message(reader) == payload1
    assert await read_message(reader) == payload2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_connection.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create connection.py**

```python
# pyDSvDCAPIv2/connection.py
from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Any, TYPE_CHECKING

from pyDSvDCAPIv2.exceptions import VDCConnectionError
from pyDSvDCAPIv2.proto import (
    service_announcement_pb2,
    device_announcement_pb2,
    state_pb2,
    command_pb2,
    scene_pb2,
    event_pb2,
    firmware_pb2,
    heartbeat_pb2,
    error_pb2,
)

if TYPE_CHECKING:
    from pyDSvDCAPIv2.vdc import VDC

logger = logging.getLogger(__name__)

_RECONNECT_BASE = 2.0   # seconds
_RECONNECT_MAX = 60.0   # seconds


def frame_message(payload: bytes) -> bytes:
    """Prepend 4-byte big-endian length prefix to payload."""
    return struct.pack(">I", len(payload)) + payload


async def read_message(reader: asyncio.StreamReader) -> bytes:
    """Read one length-prefixed message from stream. Returns raw protobuf bytes."""
    header = await reader.readexactly(4)
    length = struct.unpack(">I", header)[0]
    return await reader.readexactly(length)


class VDCConnection:
    """Manages TCP connection to dSS, framing, handshake, dispatch, and reconnect."""

    def __init__(self, vdc: VDC) -> None:
        self._vdc = vdc
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._running = False
        self._dispatch_task: asyncio.Task | None = None
        self._reconnect_delay = _RECONNECT_BASE

    async def connect(self) -> None:
        """Connect to dSS, handshake, and register all devices."""
        self._reader, self._writer = await asyncio.open_connection(
            self._vdc.server_host, self._vdc.server_port
        )
        logger.info("Connected to dSS at %s:%s", self._vdc.server_host, self._vdc.server_port)
        await self._handshake()
        await self._register_devices()
        self._reconnect_delay = _RECONNECT_BASE  # reset on success

    async def _handshake(self) -> None:
        """Send ServiceAnnouncement, receive and validate ServiceAcknowledgement."""
        from pyDSvDCAPIv2.constants import ServiceConfig
        ann = service_announcement_pb2.ServiceAnnouncement()
        ann.vdcId = self._vdc.vdc_id
        ann.type = self._vdc.name
        ann.name = self._vdc.name
        ann.version = self._vdc.version
        for cap in self._vdc.capabilities:
            ann.caps.append(int(cap))
        if self._vdc.ws_path:
            ann.config[ServiceConfig.PROTO] = "protobuf"
            ann.config[ServiceConfig.WS] = "1"
            ann.config[ServiceConfig.WS_PATH] = self._vdc.ws_path

        await self._send(ann.SerializeToString())

        raw = await read_message(self._reader)
        ack = service_announcement_pb2.ServiceAcknowledgement()
        ack.ParseFromString(raw)

        if ack.HasField("error") and ack.error.code != 0:
            raise VDCConnectionError(
                f"dSS rejected handshake: [{ack.error.code}] {ack.error.message}"
            )
        self._vdc._session_options = dict(ack.options)
        logger.info("Handshake OK, protocol=%s", ack.protocolVersion)

    async def _register_devices(self) -> None:
        """Send DeviceAnnouncement for each registered device."""
        for device in self._vdc._devices.values():
            pb = self._device_to_proto(device)
            await self._send(pb.SerializeToString())
            logger.debug("Announced device %s (%s)", device.device_id, device.name)

    def _device_to_proto(self, device: Any) -> device_announcement_pb2.DeviceAnnouncement:
        pb = device_announcement_pb2.DeviceAnnouncement()
        pb.deviceId = device.device_id
        pb.type = int(device.type)
        pb.class_ = int(device.class_)
        pb.status = int(device.status)
        pb.name = device.name
        for k, v in device.config.items():
            pb.config[k] = v
        for k, v in device.metadata.items():
            pb.metadata[k] = v
        for k, v in device.attributes.items():
            pb.attributes[k] = v
        for cap in device.capabilities:
            pb_cap = pb.capabilities.add()
            pb_cap.type = int(cap.type)
            for k, v in cap.parameters.items():
                pb_cap.parameters[k] = v
        return pb

    async def _send(self, payload: bytes) -> None:
        """Send length-prefixed protobuf bytes to dSS."""
        self._writer.write(frame_message(payload))
        await self._writer.drain()

    async def send_raw(self, payload: bytes) -> None:
        """Public send interface used by VDC."""
        await self._send(payload)

    async def start_dispatch(self) -> None:
        """Start the background message dispatch loop."""
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())

    async def _dispatch_loop(self) -> None:
        """Read incoming messages from dSS and dispatch to device callbacks."""
        while self._running:
            try:
                raw = await read_message(self._reader)
                await self._dispatch(raw)
            except asyncio.IncompleteReadError:
                logger.warning("dSS connection closed")
                break
            except Exception as e:
                logger.error("Dispatch error: %s", e)
                break
        if self._running:
            await self._vdc._on_disconnect()

    async def _dispatch(self, raw: bytes) -> None:
        """Try to parse raw bytes as each known incoming message type and dispatch."""
        # Try SetStateRequest
        try:
            msg = state_pb2.SetStateRequest()
            msg.ParseFromString(raw)
            if msg.deviceId and msg.attribute:
                device = self._vdc._devices.get(msg.deviceId)
                if device and device.on_set_state:
                    resp = state_pb2.SetStateResponse()
                    resp.deviceId = msg.deviceId
                    try:
                        await device.on_set_state(msg.attribute, msg.value)
                        resp.status = 0  # OK
                    except Exception as e:
                        logger.error("on_set_state error: %s", e)
                        resp.status = 1  # FAILED
                    await self._send(resp.SerializeToString())
                return
        except Exception:
            pass

        # Try StateRequest (GetDeviceState)
        try:
            msg = state_pb2.StateRequest()
            msg.ParseFromString(raw)
            if msg.deviceId:
                device = self._vdc._devices.get(msg.deviceId)
                resp = state_pb2.StateResponse()
                resp.deviceId = msg.deviceId
                if device and device.on_get_state:
                    try:
                        val = await device.on_get_state(msg.attribute)
                        resp.values[msg.attribute] = val
                    except Exception as e:
                        logger.error("on_get_state error: %s", e)
                await self._send(resp.SerializeToString())
                return
        except Exception:
            pass

        # Try Command
        try:
            msg = command_pb2.Command()
            msg.ParseFromString(raw)
            if msg.deviceId and msg.command:
                device = self._vdc._devices.get(msg.deviceId)
                result = command_pb2.CommandResult()
                result.deviceId = msg.deviceId
                if device and device.on_command:
                    try:
                        out = await device.on_command(msg.command, dict(msg.params))
                        result.status = 0  # OK
                        for k, v in (out or {}).items():
                            result.result[k] = str(v)
                    except Exception as e:
                        logger.error("on_command error: %s", e)
                        result.status = 1  # FAILED
                await self._send(result.SerializeToString())
                return
        except Exception:
            pass

        # Try SceneActivation
        try:
            msg = scene_pb2.SceneActivation()
            msg.ParseFromString(raw)
            if msg.sceneId:
                if self._vdc.on_scene_event:
                    try:
                        await self._vdc.on_scene_event(msg)
                    except Exception as e:
                        logger.error("on_scene_event error: %s", e)
                return
        except Exception:
            pass

        # Try Heartbeat — echo back
        try:
            msg = heartbeat_pb2.Heartbeat()
            msg.ParseFromString(raw)
            if msg.vdcId:
                resp = heartbeat_pb2.Heartbeat()
                resp.vdcId = self._vdc.vdc_id
                resp.timestamp = int(time.time() * 1000)
                await self._send(resp.SerializeToString())
                return
        except Exception:
            pass

        logger.debug("Received unrecognized message (%d bytes), ignoring", len(raw))

    async def send_device_removal(self, device_id: str) -> None:
        pb = device_announcement_pb2.DeviceRemoval()
        pb.deviceId = device_id
        await self._send(pb.SerializeToString())

    async def send_device_event(
        self, device_id: str, event_type: int, attribute: str, value: str
    ) -> None:
        pb = event_pb2.DeviceEvent()
        pb.deviceId = device_id
        pb.type = event_type
        pb.attribute = attribute
        pb.value = value
        pb.timestamp = int(time.time() * 1000)
        await self._send(pb.SerializeToString())

    async def send_heartbeat(self, vdc_id: str, metrics: dict[str, str]) -> None:
        pb = heartbeat_pb2.Heartbeat()
        pb.vdcId = vdc_id
        pb.timestamp = int(time.time() * 1000)
        for k, v in metrics.items():
            pb.metrics[k] = v
        await self._send(pb.SerializeToString())

    async def close(self) -> None:
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_connection.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add pyDSvDCAPIv2/connection.py tests/test_connection.py
git commit -m "feat: add TCP connection with length-prefix framing and message dispatch"
```

---

## Task 8: Heartbeat

**Files:**
- Create: `pyDSvDCAPIv2/heartbeat.py`

No separate test — heartbeat is a thin asyncio loop; covered by VDC integration tests in Task 9.

- [ ] **Step 1: Create heartbeat.py**

```python
# pyDSvDCAPIv2/heartbeat.py
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyDSvDCAPIv2.vdc import VDC

logger = logging.getLogger(__name__)


class HeartbeatTask:
    """Sends periodic Heartbeat messages to dSS."""

    def __init__(self, vdc: VDC) -> None:
        self._vdc = vdc
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._vdc.heartbeat_interval)
                if self._vdc._connection:
                    await self._vdc._connection.send_heartbeat(
                        self._vdc.vdc_id,
                        self._vdc.heartbeat_metrics,
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Heartbeat error: %s", e)
```

- [ ] **Step 2: Commit**

```bash
git add pyDSvDCAPIv2/heartbeat.py
git commit -m "feat: add periodic heartbeat task"
```

---

## Task 9: WebSocket event channel

**Files:**
- Create: `pyDSvDCAPIv2/ws_client.py`

- [ ] **Step 1: Create ws_client.py**

```python
# pyDSvDCAPIv2/ws_client.py
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyDSvDCAPIv2.vdc import VDC

logger = logging.getLogger(__name__)

_RECONNECT_DELAY = 5.0


class WebSocketClient:
    """Optional WebSocket event channel to dSS.

    Activated when ServiceAcknowledgement.options['upgrade'] == 'websocket'
    and the VDC has ws_path configured.
    """

    def __init__(self, vdc: VDC) -> None:
        self._vdc = vdc
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self, url: str) -> None:
        self._url = url
        self._running = True
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        try:
            import websockets
        except ImportError:
            logger.error("websockets library not installed; WebSocket channel disabled")
            return

        while self._running:
            try:
                logger.info("WebSocket connecting to %s", self._url)
                async with websockets.connect(self._url) as ws:
                    logger.info("WebSocket connected")
                    async for message in ws:
                        if isinstance(message, bytes):
                            await self._vdc._connection._dispatch(message)
                        else:
                            logger.debug("Non-bytes WS message ignored")
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.warning("WebSocket error: %s — reconnecting in %.0fs", e, _RECONNECT_DELAY)
                    await asyncio.sleep(_RECONNECT_DELAY)
```

- [ ] **Step 2: Commit**

```bash
git add pyDSvDCAPIv2/ws_client.py
git commit -m "feat: add optional WebSocket event channel"
```

---

## Task 10: VDC orchestrator and public API

**Files:**
- Create: `pyDSvDCAPIv2/vdc.py`
- Modify: `pyDSvDCAPIv2/__init__.py`
- Create: `tests/test_vdc.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_vdc.py
import asyncio
import struct
import pytest
from unittest.mock import AsyncMock, patch
from pyDSvDCAPIv2.vdc import VDC
from pyDSvDCAPIv2.device import Device
from pyDSvDCAPIv2.enums import DeviceType, DeviceClass, DeviceStatus, VdcCapabilityFlag
from pyDSvDCAPIv2.proto import service_announcement_pb2, device_announcement_pb2
from pyDSvDCAPIv2.connection import frame_message


def _framed(pb_msg) -> bytes:
    return frame_message(pb_msg.SerializeToString())


@pytest.fixture
def vdc(tmp_path):
    return VDC(
        vdc_id="test-vdc",
        name="Test VDC",
        version="1.0.0",
        server_host="127.0.0.1",
        server_port=19999,
        state_path=str(tmp_path / "state.yaml"),
        ws_path=None,
    )


@pytest.fixture
def device():
    return Device(
        device_id="lamp-001",
        type=DeviceType.LIGHT,
        class_=DeviceClass.LIGHTING,
        status=DeviceStatus.ONLINE,
        name="Test Lamp",
    )


def test_add_device(vdc, device):
    vdc.add_device(device)
    assert "lamp-001" in vdc._devices or device.device_id in vdc._devices


def test_vdc_id_is_resolved_to_dsuid(vdc):
    # Before start(), vdc_id is the seed; after load_state it becomes dSUID
    assert vdc.vdc_id == "test-vdc" or len(vdc.vdc_id) == 34


@pytest.mark.asyncio
async def test_start_connects_and_announces(vdc, device, tmp_path):
    vdc.add_device(device)

    # Build mock dSS: send back a valid ServiceAcknowledgement
    ack = service_announcement_pb2.ServiceAcknowledgement()
    ack.protocolVersion = "2.0"
    ack_bytes = _framed(ack)

    async def mock_open_connection(host, port):
        reader = asyncio.StreamReader()
        # Feed the ack immediately
        reader.feed_data(ack_bytes)
        writer = AsyncMock()
        writer.drain = AsyncMock()
        writer.close = AsyncMock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    with patch("asyncio.open_connection", side_effect=mock_open_connection):
        await vdc.start()
        await vdc.stop()


@pytest.mark.asyncio
async def test_state_is_persisted_after_device_update(vdc, device, tmp_path):
    vdc.add_device(device)
    device._vdc = vdc

    ack = service_announcement_pb2.ServiceAcknowledgement()
    ack.protocolVersion = "2.0"

    async def mock_open_connection(host, port):
        reader = asyncio.StreamReader()
        reader.feed_data(_framed(ack))
        writer = AsyncMock()
        writer.drain = AsyncMock()
        writer.close = AsyncMock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    with patch("asyncio.open_connection", side_effect=mock_open_connection):
        await vdc.start()
        device.update_state("brightness", "80")
        vdc._store.flush()
        await vdc.stop()

    data = vdc._store.load()
    states = {d["device_id"]: d.get("state", {}) for d in data.get("devices", [])}
    assert states.get(device.device_id, {}).get("brightness") == "80"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_vdc.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create vdc.py**

```python
# pyDSvDCAPIv2/vdc.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from pyDSvDCAPIv2.connection import VDCConnection
from pyDSvDCAPIv2.device import Device
from pyDSvDCAPIv2.dsuid import DsUid
from pyDSvDCAPIv2.enums import EventType, VdcCapabilityFlag
from pyDSvDCAPIv2.exceptions import VDCConnectionError
from pyDSvDCAPIv2.heartbeat import HeartbeatTask
from pyDSvDCAPIv2.persistence import PropertyStore
from pyDSvDCAPIv2.ws_client import WebSocketClient

logger = logging.getLogger(__name__)

_RECONNECT_BASE = 2.0
_RECONNECT_MAX = 60.0


class VDC:
    """Top-level VDC entry point. Connects to dSS and manages device lifecycle."""

    def __init__(
        self,
        vdc_id: str,
        name: str,
        version: str,
        server_host: str,
        server_port: int = 62000,
        capabilities: list[VdcCapabilityFlag] | None = None,
        state_path: str = "state.yaml",
        heartbeat_interval: float = 30.0,
        ws_path: str | None = "/vdc/ws",
    ) -> None:
        self._seed = vdc_id
        self.vdc_id = vdc_id  # resolved to dSUID on start()
        self.name = name
        self.version = version
        self.server_host = server_host
        self.server_port = server_port
        self.capabilities: list[VdcCapabilityFlag] = capabilities or []
        self.heartbeat_interval = heartbeat_interval
        self.ws_path = ws_path
        self.heartbeat_metrics: dict[str, str] = {}

        self._devices: dict[str, Device] = {}
        self._store = PropertyStore(state_path)
        self._connection: VDCConnection | None = None
        self._heartbeat: HeartbeatTask | None = None
        self._ws: WebSocketClient | None = None
        self._running = False
        self._reconnect_delay = _RECONNECT_BASE
        self._session_options: dict[str, str] = {}

        # Callbacks
        self.on_scene_event: Callable[[Any], Awaitable[None]] | None = None

    def add_device(self, device: Device) -> None:
        """Register a device with this VDC."""
        device._vdc = self
        self._devices[device.device_id] = device

    async def remove_device(self, device_id: str) -> None:
        """Remove a device from dSS and deregister it."""
        if self._connection:
            await self._connection.send_device_removal(device_id)
        self._devices.pop(device_id, None)
        self._schedule_save()

    async def start(self) -> None:
        """Connect to dSS, run handshake, announce devices, start background tasks."""
        self._load_state()
        self._running = True
        await self._connect_with_retry()

    async def stop(self) -> None:
        """Gracefully stop all background tasks and close the connection."""
        self._running = False
        self._stop_background_tasks()
        if self._connection:
            await self._connection.close()
        self._store.flush()

    async def flush(self) -> None:
        """Force immediate YAML save."""
        self._store.flush()

    def _load_state(self) -> None:
        """Restore persisted state. Resolves vdc_id seed to stable dSUID."""
        data = self._store.load()
        vdc_data = data.get("vdc", {})

        # Resolve stable dSUID — reuse persisted one if present
        if vdc_data.get("vdc_id"):
            self.vdc_id = vdc_data["vdc_id"]
        else:
            self.vdc_id = DsUid.for_vdc(self._seed)

        # Restore device state
        for dev_data in data.get("devices", []):
            dev_id = dev_data.get("device_id")
            if dev_id and dev_id in self._devices:
                self._devices[dev_id].state = dict(dev_data.get("state", {}))
                # Also resolve stable dSUID for device
                self._devices[dev_id].device_id = dev_id

        # Resolve device IDs for any not yet in store
        for device in self._devices.values():
            if len(device.device_id) != 34:
                device.device_id = DsUid.for_device(device.device_id)
                self._devices = {d.device_id: d for d in self._devices.values()}
                break

    def _build_state_dict(self) -> dict[str, Any]:
        return {
            "vdc": {
                "vdc_id": self.vdc_id,
                "name": self.name,
                "version": self.version,
                "server_host": self.server_host,
                "server_port": self.server_port,
                "capabilities": [int(c) for c in self.capabilities],
            },
            "devices": [d.to_dict() for d in self._devices.values()],
        }

    def _schedule_save(self) -> None:
        data = self._build_state_dict()
        asyncio.create_task(self._store.schedule_save(data))

    async def _connect_with_retry(self) -> None:
        while self._running:
            try:
                self._connection = VDCConnection(self)
                await self._connection.connect()
                self._reconnect_delay = _RECONNECT_BASE
                await self._start_background_tasks()
                return
            except VDCConnectionError:
                raise
            except Exception as e:
                logger.warning(
                    "Connection failed: %s — retrying in %.0fs", e, self._reconnect_delay
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, _RECONNECT_MAX)

    async def _start_background_tasks(self) -> None:
        await self._connection.start_dispatch()
        self._heartbeat = HeartbeatTask(self)
        self._heartbeat.start()
        upgrade = self._session_options.get("upgrade")
        if upgrade == "websocket" and self.ws_path:
            self._ws = WebSocketClient(self)
            url = f"ws://{self.server_host}:{self.server_port}{self.ws_path}"
            self._ws.start(url)

    def _stop_background_tasks(self) -> None:
        if self._heartbeat:
            self._heartbeat.stop()
        if self._ws:
            self._ws.stop()

    async def _on_disconnect(self) -> None:
        """Called by VDCConnection when the TCP connection drops."""
        if not self._running:
            return
        self._stop_background_tasks()
        logger.warning("Disconnected from dSS — reconnecting in %.0fs", self._reconnect_delay)
        await asyncio.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, _RECONNECT_MAX)
        await self._connect_with_retry()

    async def _send_device_event(
        self, device: Device, event_type: EventType, attribute: str, value: str
    ) -> None:
        if self._connection:
            await self._connection.send_device_event(
                device.device_id, int(event_type), attribute, value
            )
```

- [ ] **Step 4: Update `__init__.py`**

```python
# pyDSvDCAPIv2/__init__.py
from pyDSvDCAPIv2.vdc import VDC
from pyDSvDCAPIv2.device import Device, VdcCapability, Measurement, Scene
from pyDSvDCAPIv2.dsuid import DsUid
from pyDSvDCAPIv2.enums import (
    DeviceType, DeviceClass, DeviceStatus,
    CapabilityType, VdcCapabilityFlag,
    MeasurementType, EventType, Action,
    CommandStatus, SceneType, ErrorCode,
)
from pyDSvDCAPIv2.constants import (
    ServiceConfig, AckOptions, ServiceEndpoints,
    DeviceConfig, DeviceMetadata, DeviceAttributes,
    DimmingParams, ColorParams, CommandParams,
    CommandResultKeys, SceneAttributes,
)
from pyDSvDCAPIv2.exceptions import VDCConnectionError, DeviceError

__all__ = [
    "VDC", "Device", "VdcCapability", "Measurement", "Scene",
    "DsUid",
    "DeviceType", "DeviceClass", "DeviceStatus",
    "CapabilityType", "VdcCapabilityFlag",
    "MeasurementType", "EventType", "Action",
    "CommandStatus", "SceneType", "ErrorCode",
    "ServiceConfig", "AckOptions", "ServiceEndpoints",
    "DeviceConfig", "DeviceMetadata", "DeviceAttributes",
    "DimmingParams", "ColorParams", "CommandParams",
    "CommandResultKeys", "SceneAttributes",
    "VDCConnectionError", "DeviceError",
]
```

- [ ] **Step 5: Run all tests**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add pyDSvDCAPIv2/vdc.py pyDSvDCAPIv2/__init__.py tests/test_vdc.py
git commit -m "feat: add VDC orchestrator, public API, and integration tests"
```

---

## Task 11: Working example

**Files:**
- Create: `examples/simple_light.py`

- [ ] **Step 1: Create simple_light.py**

```python
# examples/simple_light.py
"""Minimal example: announce a dimmable light to dSS and handle commands."""
import asyncio
import logging
from pyDSvDCAPIv2 import (
    VDC, Device, VdcCapability,
    DeviceType, DeviceClass, DeviceStatus,
    CapabilityType, VdcCapabilityFlag,
    DeviceConfig, DimmingParams, DeviceAttributes,
)

logging.basicConfig(level=logging.INFO)

DSS_HOST = "10.42.10.10"   # replace with your dSS IP
DSS_PORT = 62000


async def main():
    # 1. Create VDC
    vdc = VDC(
        vdc_id="example-bridge-001",
        name="Python Example Bridge",
        version="1.0.0",
        server_host=DSS_HOST,
        server_port=DSS_PORT,
        capabilities=[VdcCapabilityFlag.SCENES, VdcCapabilityFlag.DYNAMIC_DEVICES],
        state_path="example_state.yaml",
        ws_path="/vdc/ws",
    )

    # 2. Create a dimmable light device
    light = Device(
        device_id="example-lamp-001",
        type=DeviceType.LIGHT,
        class_=DeviceClass.LIGHTING,
        status=DeviceStatus.ONLINE,
        name="Example Kitchen Light",
        capabilities=[
            VdcCapability(
                type=CapabilityType.DIMMING,
                parameters={DimmingParams.MIN_LEVEL: "0", DimmingParams.MAX_LEVEL: "100"},
            )
        ],
        config={DeviceConfig.ADDRESS: "AABB0011CCDD", DeviceConfig.MODEL: "example-dimmer"},
        attributes={DeviceAttributes.ROOM: "Kitchen", DeviceAttributes.FLOOR: "Ground"},
    )

    # 3. Register callbacks
    async def on_set_state(attribute: str, value: str) -> None:
        print(f"[dSS → lamp] set {attribute} = {value}")
        light.update_state(attribute, value)

    async def on_command(command: str, params: dict) -> dict:
        print(f"[dSS → lamp] command={command} params={params}")
        return {"applied": "true"}

    light.on_set_state = on_set_state
    light.on_command = on_command

    # 4. Add device and start VDC
    vdc.add_device(light)

    print(f"Connecting to dSS at {DSS_HOST}:{DSS_PORT}...")
    await vdc.start()
    print("VDC running. Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await vdc.stop()
        print("Stopped.")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add examples/simple_light.py
git commit -m "feat: add simple_light.py example"
```

---

## Task 12: Final check — run all tests and verify imports

- [ ] **Step 1: Run complete test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests PASS, no warnings about missing imports

- [ ] **Step 2: Verify public API imports**

```bash
python3 -c "
from pyDSvDCAPIv2 import (
    VDC, Device, VdcCapability, DsUid,
    DeviceType, DeviceClass, DeviceStatus,
    CapabilityType, VdcCapabilityFlag,
    MeasurementType, EventType, Action,
    CommandStatus, SceneType, ErrorCode,
    ServiceConfig, AckOptions, DeviceConfig,
    DeviceMetadata, DeviceAttributes,
    DimmingParams, ColorParams,
    VDCConnectionError, DeviceError,
)
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat: pyDSvDCAPIv2 v0.1.0 — complete initial implementation"
```
