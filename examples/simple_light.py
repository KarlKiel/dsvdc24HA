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
