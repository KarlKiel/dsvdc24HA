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
    SENSOR = 8  # proto name: SENSOR_DEVICE (renamed for package-scope uniqueness)
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
    DEFAULT = 0
    CUSTOM = 1
