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
