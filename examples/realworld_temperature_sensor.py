# examples/realworld_temperature_sensor.py
"""
Real-world example: temperature sensor VDC.

The VDC API v2 does NOT use zeroconf — the VDC connects out to the dSS
directly (TCP client on port 62000). Zeroconf is a v1 concept.

Features:
- Asks for dSS host/port at startup
- Derives VDC dSUID from host MAC address (stable across restarts)
- Connects to dSS, announces a temperature sensor device
- Generates randomly changing temperature values every 5 seconds
- Console menu:
    [R] Restart — stops VDC, waits 5s, restarts from YAML (tests reconnect)
    [Q] Quit clean — removes devices from dSS, deletes YAML, shuts down
"""
import asyncio
import glob
import logging
import os
import random
import sys
import uuid

from pyDSvDCAPIv2 import (
    VDC, Device, VdcCapability, Measurement,
    DeviceType, DeviceClass, DeviceStatus,
    CapabilityType, VdcCapabilityFlag, EventType,
    DsUid,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("realworld_temp")

STATE_PATH = "realworld_temp_state.yaml"


# ── helpers ──────────────────────────────────────────────────────────────────

def get_mac_address() -> str:
    """Return host MAC address as a hex string (no separators)."""
    mac = uuid.getnode()
    return f"{mac:012x}"


def ask(prompt: str, default: str) -> str:
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else default
    except EOFError:
        return default


# ── temperature loop ──────────────────────────────────────────────────────────

async def temperature_loop(sensor: Device, stop_event: asyncio.Event) -> None:
    """Generate random temperature values and report VALUE_REPORTED events."""
    temperature = round(random.uniform(20.0, 22.0), 1)
    while not stop_event.is_set():
        # Random walk ±0.5°C, clamped to 18–26°C
        temperature = round(
            max(18.0, min(26.0, temperature + random.uniform(-0.5, 0.5))), 1
        )
        sensor.update_state("temperature", str(temperature))
        if sensor.measurements:
            sensor.measurements[0].value = temperature

        print(f"  [temp] {temperature}°C")
        try:
            await sensor.send_event(EventType.VALUE_REPORTED, "temperature", str(temperature))
        except Exception as e:
            logger.warning("Failed to send temperature event: %s", e)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass


# ── VDC factory ──────────────────────────────────────────────────────────────

def build_vdc(vdc_id: str, dss_host: str, dss_port: int) -> tuple[VDC, Device]:
    vdc = VDC(
        vdc_id=vdc_id,
        name="Python Temperature Sensor VDC",
        version="1.0.0",
        server_host=dss_host,
        server_port=dss_port,
        capabilities=[VdcCapabilityFlag.SENSOR_EVENTS, VdcCapabilityFlag.DYNAMIC_DEVICES],
        state_path=STATE_PATH,
        heartbeat_interval=30.0,
        ws_path=None,
    )

    sensor = Device(
        device_id="temp-sensor-001",
        type=DeviceType.SENSOR,
        class_=DeviceClass.SENSOR,
        status=DeviceStatus.ONLINE,
        name="Living Room Temperature",
        capabilities=[VdcCapability(type=CapabilityType.TEMPERATURE)],
        measurements=[Measurement(type="temperature", value=20.0, unit="°C")],
    )

    async def on_get_state(attribute: str) -> str:
        return sensor.state.get(attribute, "")

    sensor.on_get_state = on_get_state
    vdc.add_device(sensor)
    return vdc, sensor


# ── clean quit ────────────────────────────────────────────────────────────────

def delete_state_files() -> None:
    for pattern in [STATE_PATH, STATE_PATH + ".bak", STATE_PATH + ".tmp"]:
        for path in glob.glob(pattern):
            try:
                os.remove(path)
                logger.info("Deleted %s", path)
            except OSError as e:
                logger.warning("Could not delete %s: %s", path, e)


# ── console menu ──────────────────────────────────────────────────────────────

async def console_menu(
    vdc_id: str,
    dss_host: str,
    dss_port: int,
    vdc: VDC,
    stop_temp: asyncio.Event,
) -> tuple:
    """Run the interactive console menu in a thread-executor loop."""
    loop = asyncio.get_running_loop()

    while True:
        try:
            choice = await loop.run_in_executor(
                None,
                lambda: input("\n[R] Restart VDC  [Q] Quit clean  > ").strip().upper(),
            )
        except EOFError:
            choice = "Q"

        if choice == "R":
            print("\nStopping VDC (5 second pause to simulate downtime)...")
            stop_temp.set()
            await vdc.stop()
            await asyncio.sleep(5.0)

            print("Restarting VDC from saved state...")
            new_vdc, new_sensor = build_vdc(vdc_id, dss_host, dss_port)
            return "restart", new_vdc, new_sensor

        elif choice == "Q":
            print("\nRemoving devices from dSS...")
            stop_temp.set()
            for device in list(vdc._devices.values()):
                await vdc.remove_device(device.device_id)
            await asyncio.sleep(0.5)
            await vdc.stop()

            print("Deleting state files...")
            delete_state_files()

            print("\nGoodbye! VDC shut down cleanly.")
            return "quit", None, None


# ── main ─────────────────────────────────────────────────────────────────────

async def run() -> None:
    print("=== pyDSvDCAPIv2 Real-World Temperature Sensor Example ===\n")

    dss_host = ask("dSS host IP", "10.42.10.10")
    dss_port = int(ask("dSS port", "62000"))

    mac_hex = get_mac_address()
    vdc_id = DsUid.for_vdc(mac_hex)
    print(f"\nHost MAC: {mac_hex}")
    print(f"VDC dSUID: {vdc_id}\n")

    vdc, sensor = build_vdc(vdc_id, dss_host, dss_port)

    while True:
        print(f"Connecting to dSS at {dss_host}:{dss_port} ...")
        try:
            await vdc.start()
        except Exception as e:
            logger.error("Failed to start VDC: %s", e)
            sys.exit(1)

        print("VDC running. Temperature updates every 5 seconds.\n")

        stop_temp = asyncio.Event()
        temp_task = asyncio.create_task(temperature_loop(sensor, stop_temp))
        menu_task = asyncio.create_task(
            console_menu(vdc_id, dss_host, dss_port, vdc, stop_temp)
        )

        done, pending = await asyncio.wait(
            {temp_task, menu_task}, return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        result = menu_task.result() if menu_task in done else None

        if result is None or result[0] == "quit":
            break

        _action, vdc, sensor = result
        print("VDC restarted. Resuming temperature updates...\n")

    logger.info("Exiting.")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
