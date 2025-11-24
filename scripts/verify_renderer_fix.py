#!/usr/bin/env python3
"""
Quick verification script to test the renderer fix.

This script creates a simple renderer test that will now show errors clearly
if the present() method is failing.

Run on the Pi as: sudo python3 scripts/verify_renderer_fix.py
"""

import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
from PIL import Image, ImageDraw

# Set up verbose logging to see all debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run a simple renderer test."""
    logger.info("=" * 60)
    logger.info("Renderer Fix Verification")
    logger.info("=" * 60)

    try:
        from hardware.framebuffer import Framebuffer
        from ui.renderer_v2 import FramebufferRendererV2

        # Initialize framebuffer
        logger.info("Initializing framebuffer...")
        fb = Framebuffer(device="/dev/fb1")
        logger.info(f"Framebuffer: {fb.width}x{fb.height}")

        # Initialize renderer
        logger.info("Initializing renderer...")
        renderer = FramebufferRendererV2(framebuffer=fb, screen_manager=None)
        logger.info("Renderer initialized successfully")

        # Test 1: Red screen
        logger.info("")
        logger.info("Test 1: Rendering red screen...")
        renderer.clear((255, 0, 0))
        renderer.draw.text((10, 10), "Fix Verification: RED", fill=(255, 255, 255))
        renderer.present()
        logger.info("SUCCESS: Red screen presented")
        time.sleep(2)

        # Test 2: Green screen
        logger.info("")
        logger.info("Test 2: Rendering green screen...")
        renderer.clear((0, 255, 0))
        renderer.draw.text((10, 10), "Fix Verification: GREEN", fill=(0, 0, 0))
        renderer.present()
        logger.info("SUCCESS: Green screen presented")
        time.sleep(2)

        # Test 3: Blue screen
        logger.info("")
        logger.info("Test 3: Rendering blue screen...")
        renderer.clear((0, 0, 255))
        renderer.draw.text((10, 10), "Fix Verification: BLUE", fill=(255, 255, 255))
        renderer.present()
        logger.info("SUCCESS: Blue screen presented")
        time.sleep(2)

        # Test 4: Pattern
        logger.info("")
        logger.info("Test 4: Rendering pattern...")
        renderer.clear((0, 0, 0))
        for i in range(0, renderer.width, 20):
            renderer.draw.line((i, 0, i, renderer.height), fill=(255, 255, 255), width=2)
        for i in range(0, renderer.height, 20):
            renderer.draw.line((0, i, renderer.width, i), fill=(255, 255, 255), width=2)
        renderer.draw.text((10, 10), "Fix Verification: GRID", fill=(255, 255, 0))
        renderer.present()
        logger.info("SUCCESS: Pattern presented")

        logger.info("")
        logger.info("=" * 60)
        logger.info("ALL TESTS PASSED!")
        logger.info("=" * 60)
        logger.info("The renderer is now working correctly.")
        logger.info("You should see 4 different patterns on the display:")
        logger.info("  1. Red background with white text")
        logger.info("  2. Green background with black text")
        logger.info("  3. Blue background with white text")
        logger.info("  4. Grid pattern with yellow text")

        fb.close()
        return 0

    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("TEST FAILED!")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("")
        logger.error("The error above should give you details about what went wrong.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
