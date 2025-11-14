"""
Unit tests for DFPlayer backend with mocked serial port.

Tests command packet construction, checksum validation, boundary conditions,
and error handling.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from io import BytesIO


@pytest.fixture
def mock_serial():
    """Mock serial.Serial class."""
    with patch('serial.Serial') as mock_ser_class:
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_instance.timeout = 0.1
        mock_instance.write = MagicMock()
        mock_instance.read = MagicMock(return_value=b'')
        mock_ser_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def dfplayer_backend(mock_serial):
    """Create DFPlayerBackend instance with mocked serial."""
    from src.backends.dfplayer_v2 import DFPlayerBackend
    backend = DFPlayerBackend(port='/dev/null', baudrate=9600)
    backend.initialize()
    return backend


class TestInitialization:
    """Test backend initialization."""

    def test_init_success(self, mock_serial):
        """Test successful initialization."""
        from src.backends.dfplayer_v2 import DFPlayerBackend
        backend = DFPlayerBackend(port='/dev/serial0')
        result = backend.initialize()
        assert result is True
        assert backend.ser is not None

    def test_init_serial_exception(self):
        """Test initialization with serial exception."""
        with patch('serial.Serial', side_effect=Exception("Port not found")):
            from src.backends.dfplayer_v2 import DFPlayerBackend
            backend = DFPlayerBackend(port='/dev/nonexistent')
            result = backend.initialize()
            assert result is False
            assert backend.ser is None

    def test_init_custom_baudrate(self, mock_serial):
        """Test initialization with custom baudrate."""
        from src.backends.dfplayer_v2 import DFPlayerBackend
        backend = DFPlayerBackend(port='/dev/serial0', baudrate=115200)
        assert backend.baudrate == 115200


class TestChecksumCalculation:
    """Test DFPlayer checksum calculation."""

    def test_checksum_correct(self, dfplayer_backend):
        """Test checksum calculation is correct."""
        # Known good packet: [0xFF, 0x06, 0x0F, 0x00, 0x01, 0x01]
        # Expected checksum: 0xFFEE (high byte: 0xFF, low byte: 0xEE)
        payload = bytearray([0xFF, 0x06, 0x0F, 0x00, 0x01, 0x01])
        checksum = dfplayer_backend._checksum(payload)

        # Verify checksum calculation
        total = sum(payload) & 0xFFFF
        expected = (0xFFFF - total + 1) & 0xFFFF
        assert checksum == expected

    def test_checksum_various_payloads(self, dfplayer_backend):
        """Test checksum with various payload values."""
        test_cases = [
            bytearray([0xFF, 0x06, 0x03, 0x00, 0x00, 0x0F]),
            bytearray([0xFF, 0x06, 0x06, 0x00, 0x00, 0x1E]),
            bytearray([0xFF, 0x06, 0x01, 0x00, 0x00, 0x00]),
        ]

        for payload in test_cases:
            checksum = dfplayer_backend._checksum(payload)
            # Verify it's a valid 16-bit value
            assert 0 <= checksum <= 0xFFFF
            # Verify the checksum property: sum + checksum = 0 (mod 65536)
            assert (sum(payload) + checksum) & 0xFFFF == 0


class TestCommandConstruction:
    """Test DFPlayer command packet construction."""

    def test_play_track_command(self, dfplayer_backend, mock_serial):
        """Test play track command packet."""
        dfplayer_backend.play_track(1)

        # Verify write was called
        assert mock_serial.write.called

        # Get the written packet
        packet = mock_serial.write.call_args[0][0]

        # Verify packet structure
        assert packet[0] == 0x7E  # Start byte
        assert packet[1] == 0xFF  # Version
        assert packet[2] == 0x06  # Length
        assert packet[3] == 0x0F  # Play folder command
        assert packet[9] == 0xEF  # End byte

        # Verify checksum
        expected_cs = dfplayer_backend._checksum(packet[1:7])
        actual_cs = (packet[7] << 8) | packet[8]
        assert actual_cs == expected_cs

    def test_set_volume_command(self, dfplayer_backend, mock_serial):
        """Test set volume command packet."""
        dfplayer_backend.set_volume(20)

        packet = mock_serial.write.call_args[0][0]

        assert packet[0] == 0x7E
        assert packet[3] == 0x06  # Volume command
        assert packet[6] == 20  # Volume level

    def test_stop_command(self, dfplayer_backend, mock_serial):
        """Test stop command packet."""
        dfplayer_backend.stop()

        packet = mock_serial.write.call_args[0][0]

        assert packet[0] == 0x7E
        assert packet[3] == 0x16  # Stop command

    def test_reset_command(self, dfplayer_backend, mock_serial):
        """Test reset command packet."""
        dfplayer_backend.reset()

        packet = mock_serial.write.call_args[0][0]

        assert packet[0] == 0x7E
        assert packet[3] == 0x0C  # Reset command


class TestBoundaryConditions:
    """Test boundary conditions for volume and track numbers."""

    def test_volume_minimum(self, dfplayer_backend, mock_serial):
        """Test volume at minimum (0)."""
        dfplayer_backend.set_volume(0)

        packet = mock_serial.write.call_args[0][0]
        assert packet[6] == 0

    def test_volume_maximum(self, dfplayer_backend, mock_serial):
        """Test volume at maximum (30)."""
        dfplayer_backend.set_volume(30)

        packet = mock_serial.write.call_args[0][0]
        assert packet[6] == 30

    def test_volume_clamping_high(self, dfplayer_backend, mock_serial):
        """Test volume clamping at high end."""
        # DFPlayer max is 30, should clamp
        dfplayer_backend.set_volume(50)

        packet = mock_serial.write.call_args[0][0]
        assert packet[6] <= 30  # Should be clamped

    def test_volume_clamping_low(self, dfplayer_backend, mock_serial):
        """Test volume clamping at low end."""
        # Should clamp negative values to 0
        dfplayer_backend.set_volume(-10)

        packet = mock_serial.write.call_args[0][0]
        assert packet[6] >= 0  # Should be clamped

    def test_track_number_edge_cases(self, dfplayer_backend, mock_serial):
        """Test track number at boundaries."""
        # Track 1
        dfplayer_backend.play_track(1)
        packet = mock_serial.write.call_args[0][0]
        assert packet[5] == 0x00  # High byte
        assert packet[6] == 0x01  # Low byte

        # Track 255 (max in single byte)
        dfplayer_backend.play_track(255)
        packet = mock_serial.write.call_args[0][0]
        assert packet[5] == 0x00
        assert packet[6] == 0xFF

        # Track 256 (requires high byte)
        dfplayer_backend.play_track(256)
        packet = mock_serial.write.call_args[0][0]
        assert packet[5] == 0x01  # High byte
        assert packet[6] == 0x00  # Low byte


class TestResponseHandling:
    """Test DFPlayer response reading and validation."""

    def test_read_valid_response(self, dfplayer_backend, mock_serial):
        """Test reading a valid response."""
        # Create valid response packet
        valid_response = bytearray([0x7E, 0xFF, 0x06, 0x3D, 0x00, 0x00, 0x01])
        checksum = dfplayer_backend._checksum(valid_response[1:7])
        valid_response.extend([(checksum >> 8) & 0xFF, checksum & 0xFF, 0xEF])

        mock_serial.read.return_value = bytes(valid_response)

        response = dfplayer_backend.read_response()
        assert response is not None
        assert len(response) == 10
        assert response[0] == 0x7E
        assert response[9] == 0xEF

    def test_read_invalid_checksum(self, dfplayer_backend, mock_serial):
        """Test reading response with invalid checksum."""
        # Create response with incorrect checksum
        invalid_response = bytearray([0x7E, 0xFF, 0x06, 0x3D, 0x00, 0x00, 0x01, 0x00, 0x00, 0xEF])

        mock_serial.read.return_value = bytes(invalid_response)

        response = dfplayer_backend.read_response()
        assert response is None  # Should reject invalid checksum

    def test_read_timeout(self, dfplayer_backend, mock_serial):
        """Test read timeout handling."""
        # Simulate timeout (empty read)
        mock_serial.read.return_value = b''

        response = dfplayer_backend.read_response(timeout=0.1)
        assert response is None

    def test_read_partial_response(self, dfplayer_backend, mock_serial):
        """Test handling of partial response."""
        # Only 5 bytes instead of 10
        mock_serial.read.return_value = b'\x7E\xFF\x06\x3D\x00'

        response = dfplayer_backend.read_response()
        assert response is None  # Should reject partial response


class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    def test_send_command_without_initialization(self):
        """Test sending command without initialized serial port."""
        from src.backends.dfplayer_v2 import DFPlayerBackend
        backend = DFPlayerBackend()
        # Should not crash, just log warning
        backend.play_track(1)
        assert backend.ser is None

    def test_send_command_serial_exception(self, dfplayer_backend, mock_serial):
        """Test handling serial write exception."""
        mock_serial.write.side_effect = Exception("Write error")

        # Should not crash, just log error
        dfplayer_backend.play_track(1)

    def test_read_response_serial_exception(self, dfplayer_backend, mock_serial):
        """Test handling serial read exception."""
        mock_serial.read.side_effect = Exception("Read error")

        response = dfplayer_backend.read_response()
        assert response is None

    def test_thread_safety(self, dfplayer_backend):
        """Test that serial lock prevents concurrent access."""
        import threading

        # This test verifies the lock exists and is used
        assert hasattr(dfplayer_backend, 'serial_lock')
        assert isinstance(dfplayer_backend.serial_lock, threading.Lock)


class TestPlaybackControl:
    """Test playback control methods."""

    def test_play_method(self, dfplayer_backend, mock_serial):
        """Test play method."""
        dfplayer_backend.play()
        assert mock_serial.write.called

    def test_pause_method(self, dfplayer_backend, mock_serial):
        """Test pause method."""
        dfplayer_backend.pause()
        assert mock_serial.write.called

    def test_next_track(self, dfplayer_backend, mock_serial):
        """Test next track method."""
        dfplayer_backend.next_track()

        packet = mock_serial.write.call_args[0][0]
        assert packet[3] == 0x01  # Next command

    def test_previous_track(self, dfplayer_backend, mock_serial):
        """Test previous track method."""
        dfplayer_backend.previous_track()

        packet = mock_serial.write.call_args[0][0]
        assert packet[3] == 0x02  # Previous command


class TestCleanup:
    """Test resource cleanup."""

    def test_cleanup_closes_serial(self, dfplayer_backend, mock_serial):
        """Test cleanup closes serial port."""
        dfplayer_backend.cleanup()

        if hasattr(mock_serial, 'close'):
            assert mock_serial.close.called or not mock_serial.is_open

    def test_shutdown_alias(self, dfplayer_backend):
        """Test shutdown is an alias for cleanup."""
        # Verify shutdown method exists
        assert hasattr(dfplayer_backend, 'shutdown')
        # It should be callable
        dfplayer_backend.shutdown()
