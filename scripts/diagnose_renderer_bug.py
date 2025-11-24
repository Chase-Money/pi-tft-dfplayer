#!/usr/bin/env python3
"""
Diagnostic script to identify why FramebufferRendererV2 isn't writing to /dev/fb1.

This script will:
1. Test direct framebuffer writes (baseline test)
2. Test renderer initialization
3. Test backbuffer creation
4. Test the complete render pipeline with detailed logging
5. Identify where the failure occurs

Run this on the Pi as: sudo python3 scripts/diagnose_renderer_bug.py
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PIL import Image, ImageDraw
from hardware.framebuffer import Framebuffer
from ui.renderer_v2 import FramebufferRendererV2
from ui.framework_v2.manager import ScreenManagerV2
from core.state_v2 import AppState

# Configure verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_1_direct_framebuffer_write():
    """Test 1: Direct framebuffer write with simple pattern."""
    logger.info("=" * 60)
    logger.info("TEST 1: Direct framebuffer write")
    logger.info("=" * 60)

    try:
        fb = Framebuffer(device="/dev/fb1")
        logger.info(f"Framebuffer opened: {fb.width}x{fb.height}")
        logger.info(f"Framebuffer device: {fb.device}")
        logger.info(f"Framebuffer mmap size: {len(fb.mm)} bytes")

        # Create red test pattern
        img = Image.new("RGB", (fb.width, fb.height), color=(255, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "TEST 1: Direct FB Write", fill=(255, 255, 255))

        logger.info("Pushing red test pattern to framebuffer...")
        fb.push(img)
        logger.info("SUCCESS: Test pattern pushed")

        time.sleep(2)

        # Create green test pattern
        img = Image.new("RGB", (fb.width, fb.height), color=(0, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "TEST 1: Second Pattern", fill=(0, 0, 0))

        logger.info("Pushing green test pattern to framebuffer...")
        fb.push(img)
        logger.info("SUCCESS: Second test pattern pushed")

        fb.close()
        return True

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        return False


def test_2_renderer_initialization():
    """Test 2: Renderer initialization without screen manager."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 2: Renderer initialization")
    logger.info("=" * 60)

    try:
        fb = Framebuffer(device="/dev/fb1")
        logger.info(f"Framebuffer opened: {fb.width}x{fb.height}")

        # Initialize renderer without screen manager
        renderer = FramebufferRendererV2(framebuffer=fb, screen_manager=None)
        logger.info(f"Renderer created: {renderer.width}x{renderer.height}")
        logger.info(f"Renderer fb reference: {renderer.fb}")
        logger.info(f"Renderer backbuffer: {renderer.backbuffer}")
        logger.info(f"Renderer backbuffer size: {renderer.backbuffer.size}")
        logger.info(f"Renderer backbuffer mode: {renderer.backbuffer.mode}")

        # Test direct backbuffer manipulation
        renderer.draw.rectangle((0, 0, renderer.width, renderer.height), fill=(0, 0, 255))
        renderer.draw.text((10, 10), "TEST 2: Renderer Init", fill=(255, 255, 0))

        logger.info("Calling renderer.present()...")
        renderer.present()
        logger.info("SUCCESS: Present completed")

        time.sleep(2)

        # Test clear and present
        renderer.clear((255, 255, 0))
        renderer.draw.text((10, 10), "TEST 2: After Clear", fill=(0, 0, 0))
        logger.info("Calling renderer.present() again...")
        renderer.present()
        logger.info("SUCCESS: Second present completed")

        fb.close()
        return True

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        return False


def test_3_full_renderer_pipeline():
    """Test 3: Full renderer pipeline with screen manager."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 3: Full renderer pipeline with screen manager")
    logger.info("=" * 60)

    try:
        fb = Framebuffer(device="/dev/fb1")
        logger.info(f"Framebuffer opened: {fb.width}x{fb.height}")

        # Create minimal state
        tracks = [{"number": i, "title": f"Track {i}"} for i in range(1, 6)]
        state = AppState(tracks=tracks)
        logger.info(f"State created with {len(state.tracks)} tracks")

        # Create screen manager
        services = {"state": state, "backend": None, "app": None, "config": None}
        screen_manager = ScreenManagerV2(services=services)
        logger.info("Screen manager created")

        # Initialize renderer with screen manager
        renderer = FramebufferRendererV2(
            framebuffer=fb,
            screen_manager=screen_manager
        )
        logger.info(f"Renderer created with screen manager")
        logger.info(f"Renderer.fb: {renderer.fb}")
        logger.info(f"Renderer.screen_manager: {renderer.screen_manager}")

        # Register a minimal test screen
        from ui.framework_v2.screen import Screen

        class TestScreen(Screen):
            def render(self, context):
                draw = context["draw"]
                width = context["width"]
                height = context["height"]

                # Draw test pattern
                draw.rectangle((0, 0, width, height), fill=(255, 0, 255))
                draw.rectangle((10, 10, width - 10, height - 10), outline=(255, 255, 255), width=2)
                draw.text((20, 20), "TEST 3: Full Pipeline", fill=(255, 255, 255))

        screen_manager.register("test", TestScreen)
        screen_manager.push("test")
        logger.info("Test screen registered and pushed")

        # Test render without present
        logger.info("Calling renderer.render()...")
        renderer.render()
        logger.info("SUCCESS: Render completed")

        # Inspect backbuffer after render
        logger.info(f"Backbuffer after render: {renderer.backbuffer.size}, mode={renderer.backbuffer.mode}")

        # Test present
        logger.info("Calling renderer.present()...")
        renderer.present()
        logger.info("SUCCESS: Present completed")

        time.sleep(2)

        # Test render_and_present convenience method
        logger.info("Calling renderer.render_and_present()...")
        renderer.render_and_present()
        logger.info("SUCCESS: render_and_present completed")

        fb.close()
        return True

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        return False


def test_4_backbuffer_inspection():
    """Test 4: Detailed backbuffer inspection and RGB565 conversion."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 4: Backbuffer inspection and RGB565 conversion")
    logger.info("=" * 60)

    try:
        fb = Framebuffer(device="/dev/fb1")
        logger.info(f"Framebuffer opened: {fb.width}x{fb.height}")

        renderer = FramebufferRendererV2(framebuffer=fb, screen_manager=None)

        # Draw simple pattern
        renderer.clear((128, 64, 192))
        renderer.draw.rectangle((50, 50, 150, 150), fill=(255, 255, 0))

        logger.info("Backbuffer details:")
        logger.info(f"  Size: {renderer.backbuffer.size}")
        logger.info(f"  Mode: {renderer.backbuffer.mode}")
        logger.info(f"  Format: {renderer.backbuffer.format}")

        # Test RGB565 conversion directly
        logger.info("Testing RGB565 conversion...")
        rgb565_data = fb._rgb888_to_rgb565le(renderer.backbuffer.convert("RGB"))
        logger.info(f"  RGB565 buffer shape: {rgb565_data.shape}")
        logger.info(f"  RGB565 buffer dtype: {rgb565_data.dtype}")
        logger.info(f"  RGB565 buffer size: {rgb565_data.nbytes} bytes")
        logger.info(f"  Expected size: {fb.width * fb.height * 2} bytes")

        if rgb565_data.nbytes == fb.width * fb.height * 2:
            logger.info("SUCCESS: RGB565 conversion produces correct size")
        else:
            logger.error("ERROR: RGB565 conversion size mismatch!")

        # Test memoryview creation
        logger.info("Testing memoryview creation...")
        mv = memoryview(rgb565_data)
        logger.info(f"  Memoryview: {len(mv)} bytes, format={mv.format}")

        # Test mmap write
        logger.info("Testing mmap write...")
        fb.mm.seek(0)
        bytes_written = fb.mm.write(mv)
        logger.info(f"  Bytes written: {bytes_written}")

        logger.info("SUCCESS: All backbuffer operations completed")

        fb.close()
        return True

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        return False


def test_5_exception_detection():
    """Test 5: Force exceptions to test error handling."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 5: Exception detection in present()")
    logger.info("=" * 60)

    try:
        fb = Framebuffer(device="/dev/fb1")
        renderer = FramebufferRendererV2(framebuffer=fb, screen_manager=None)

        # Test 1: Normal present (should work)
        renderer.clear((255, 0, 0))
        logger.info("Test 5a: Normal present...")
        renderer.present()
        logger.info("SUCCESS: Normal present worked")

        time.sleep(1)

        # Test 2: Close framebuffer and try present (should fail)
        logger.info("Test 5b: Present after closing framebuffer...")
        fb.mm.close()
        fb.fb_file.close()

        renderer.clear((0, 255, 0))
        logger.info("Attempting present with closed framebuffer...")
        renderer.present()  # This should fail but error is caught
        logger.info("Present call returned (check if error was logged above)")

        return True

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        return False


def main():
    """Run all diagnostic tests."""
    logger.info("Starting FramebufferRendererV2 diagnostic suite")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info("")

    results = {
        "Test 1: Direct framebuffer write": test_1_direct_framebuffer_write(),
        "Test 2: Renderer initialization": test_2_renderer_initialization(),
        "Test 3: Full renderer pipeline": test_3_full_renderer_pipeline(),
        "Test 4: Backbuffer inspection": test_4_backbuffer_inspection(),
        "Test 5: Exception detection": test_5_exception_detection(),
    }

    logger.info("")
    logger.info("=" * 60)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        logger.info("")
        logger.info("All tests passed - renderer should be working!")
    else:
        logger.info("")
        logger.info("Some tests failed - check logs above for details")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
