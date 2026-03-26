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
