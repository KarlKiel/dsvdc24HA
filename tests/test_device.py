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
