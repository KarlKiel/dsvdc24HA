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
