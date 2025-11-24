"""Test fixtures for DFPlayer application testing."""

from .mock_hardware import (
    MockFramebuffer,
    MockTouchDevice,
    MockDFPlayerSerial,
    create_mock_hardware_suite
)

__all__ = [
    "MockFramebuffer",
    "MockTouchDevice",
    "MockDFPlayerSerial",
    "create_mock_hardware_suite"
]
