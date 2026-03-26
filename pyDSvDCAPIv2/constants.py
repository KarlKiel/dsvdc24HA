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
