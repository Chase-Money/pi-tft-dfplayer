"""
Integrated test suite for code quality checks.
Tests resource cleanup, error handling, and function existence without requiring hardware.
"""
import pytest
import sys
import os
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestResourceCleanup:
    """Test that resource cleanup code exists."""

    def test_cleanup_function_exists(self):
        """Verify cleanup() function is defined."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        assert 'def cleanup():' in content, "cleanup() function should be defined"

    def test_atexit_register_called(self):
        """Verify atexit.register(cleanup) is called."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        assert 'atexit.register(cleanup)' in content, \
            "cleanup should be registered with atexit"

    def test_cleanup_closes_serial(self):
        """Verify cleanup closes serial port."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find cleanup function
        pattern = r'def cleanup\(\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "cleanup function should exist"

        func_body = match.group(0)

        assert 'ser.close()' in func_body, "cleanup should close serial port"

    def test_cleanup_closes_mmap_and_fb(self):
        """Verify cleanup closes memory map and framebuffer."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find cleanup function
        pattern = r'def cleanup\(\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "cleanup function should exist"

        func_body = match.group(0)

        assert 'mm.close()' in func_body, "cleanup should close memory map"
        assert 'fb.close()' in func_body, "cleanup should close framebuffer"

    def test_cleanup_has_exception_handling(self):
        """Verify cleanup has try/except blocks."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find cleanup function
        pattern = r'def cleanup\(\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "cleanup function should exist"

        func_body = match.group(0)

        # Count try blocks
        try_count = func_body.count('try:')
        except_count = func_body.count('except')

        assert try_count >= 3, "cleanup should have try blocks for each resource"
        assert except_count >= 3, "cleanup should have except blocks for each resource"


class TestErrorHandling:
    """Test that error handling functions exist."""

    def test_init_serial_function_exists(self):
        """Verify init_serial() function exists."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        assert 'def init_serial():' in content, "init_serial() function should be defined"

    def test_init_serial_has_exception_handling(self):
        """Verify init_serial() has try/except."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find init_serial function
        pattern = r'def init_serial\(\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "init_serial function should exist"

        func_body = match.group(0)

        assert 'try:' in func_body, "init_serial should have try block"
        assert 'except serial.SerialException' in func_body, \
            "init_serial should catch SerialException"
        assert 'except PermissionError' in func_body, \
            "init_serial should catch PermissionError"

    def test_init_touch_function_exists(self):
        """Verify init_touch() function exists."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        assert 'def init_touch():' in content, "init_touch() function should be defined"

    def test_init_touch_has_exception_handling(self):
        """Verify init_touch() has try/except."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find init_touch function
        pattern = r'def init_touch\(\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "init_touch function should exist"

        func_body = match.group(0)

        assert 'try:' in func_body, "init_touch should have try block"
        assert 'except RuntimeError' in func_body, \
            "init_touch should catch RuntimeError"
        assert 'except PermissionError' in func_body, \
            "init_touch should catch PermissionError"

    def test_send_has_error_handling(self):
        """Verify send() function has error handling."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find send function
        pattern = r'def send\([^)]*\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "send function should exist"

        func_body = match.group(0)

        assert 'if ser is None' in func_body or 'ser is None' in func_body, \
            "send should check if ser is None"
        assert 'if not ser.is_open' in func_body or 'ser.is_open' in func_body, \
            "send should check if serial port is open"
        assert 'try:' in func_body, "send should have try block"
        assert 'except serial.SerialException' in func_body, \
            "send should catch SerialException"

    def test_logging_configured(self):
        """Verify logging is set up."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        assert 'logging' in content, "logging module should be imported"
        assert 'logger' in content, "logger should be configured"
        assert 'logger.error' in content or 'logger.info' in content, \
            "logger should be used for logging"


class TestMainLoopProtection:
    """Test that main_loop checks for touch device."""

    def test_main_loop_checks_touch(self):
        """Verify main_loop checks if touch is None."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find main_loop function
        pattern = r'def main_loop\(\):.*?(?=\nif __name__|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "main_loop function should exist"

        func_body = match.group(0)

        assert 'if touch is None' in func_body or 'touch is None' in func_body, \
            "main_loop should check if touch device is initialized"
