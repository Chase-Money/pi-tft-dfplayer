import serial
import types
from backends.robust_serial import RobustSerial


class FakeSerial:
    """Minimal serial.Serial stand-in for RobustSerial tests."""

    def __init__(self, *args, **kwargs):
        self.is_open = True
        self.timeout = kwargs.get("timeout")
        self.writes = []
        self.read_responses = []
        self.raise_on_write = False
        self.raise_on_read = False

    def write(self, data):
        if self.raise_on_write:
            self.raise_on_write = False
            raise serial.SerialException("write failed")
        self.writes.append(data)
        return len(data)

    def read(self, size=1):
        if self.raise_on_read:
            self.raise_on_read = False
            raise serial.SerialException("read failed")
        if self.read_responses:
            return self.read_responses.pop(0)
        return b""

    def close(self):
        self.is_open = False


def test_write_reconnects_on_error(monkeypatch):
    """RobustSerial should reconnect and retry writes after a SerialException."""
    instances = []

    def fake_serial(*args, **kwargs):
        inst = FakeSerial(*args, **kwargs)
        instances.append(inst)
        return inst

    monkeypatch.setattr(serial, "Serial", fake_serial)

    rs = RobustSerial("/dev/test", 9600, timeout=0.1, reconnect_delay=0)
    # First instance fails on write, second should succeed
    instances[0].raise_on_write = True
    assert rs.write(b"hello") is True
    assert len(instances) == 2
    assert instances[1].writes == [b"hello"]


def test_read_reconnects_on_error(monkeypatch):
    """RobustSerial should reconnect and retry reads after a SerialException."""
    instances = []

    def fake_serial(*args, **kwargs):
        inst = FakeSerial(*args, **kwargs)
        instances.append(inst)
        return inst

    monkeypatch.setattr(serial, "Serial", fake_serial)

    rs = RobustSerial("/dev/test", 9600, timeout=0.1, reconnect_delay=0)
    instances[0].raise_on_read = True
    # Prepare second connection to return data
    def after_connect(*args, **kwargs):
        inst = FakeSerial(*args, **kwargs)
        inst.read_responses.append(b"ok")
        instances.append(inst)
        return inst

    monkeypatch.setattr(serial, "Serial", after_connect)
    result = rs.read(2)
    assert result == b"ok"
    assert len(instances) == 2


def test_timeout_property_updates_serial(monkeypatch):
    """Updating timeout property should propagate to active serial connection."""
    def fake_serial(*args, **kwargs):
        return FakeSerial(*args, **kwargs)

    monkeypatch.setattr(serial, "Serial", fake_serial)
    rs = RobustSerial("/dev/test", 9600, timeout=0.2, reconnect_delay=0)
    assert rs.timeout == 0.2
    rs.timeout = 0.5
    assert rs.timeout == 0.5
    assert rs.ser.timeout == 0.5
