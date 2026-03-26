class VDCConnectionError(Exception):
    """Raised when the VDC cannot connect to dSS or handshake fails."""


class DeviceError(Exception):
    """Raised when a device operation returns a non-OK status from dSS."""
