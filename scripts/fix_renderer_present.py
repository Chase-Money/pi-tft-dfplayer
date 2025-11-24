#!/usr/bin/env python3
"""
Fix script for the renderer present() bug.

This script patches the FramebufferRendererV2 to add verbose error reporting
and removes the exception swallowing behavior.

Usage:
    python3 scripts/fix_renderer_present.py
"""

import sys
from pathlib import Path

# Path to the renderer file
RENDERER_FILE = Path(__file__).parent.parent / "src" / "ui" / "renderer_v2" / "renderer.py"
BACKUP_FILE = RENDERER_FILE.with_suffix(".py.backup")

def main():
    print("=" * 60)
    print("FramebufferRendererV2 present() Bug Fix")
    print("=" * 60)

    if not RENDERER_FILE.exists():
        print(f"ERROR: Renderer file not found: {RENDERER_FILE}")
        return 1

    # Read current content
    with open(RENDERER_FILE, 'r') as f:
        content = f.read()

    # Create backup
    print(f"Creating backup: {BACKUP_FILE}")
    with open(BACKUP_FILE, 'w') as f:
        f.write(content)

    # Apply fix
    old_present = '''    def present(self) -> None:
        """
        Present the backbuffer to the hardware framebuffer.

        This performs the actual framebuffer write and should be called
        after render() to display the frame.
        """
        try:
            self.fb.push(self.backbuffer)
        except Exception as e:
            logger.error(f"Failed to present to framebuffer: {e}")'''

    new_present = '''    def present(self) -> None:
        """
        Present the backbuffer to the hardware framebuffer.

        This performs the actual framebuffer write and should be called
        after render() to display the frame.
        """
        try:
            # Validate framebuffer reference
            if self.fb is None:
                logger.error("CRITICAL: Framebuffer reference is None!")
                raise RuntimeError("Framebuffer not initialized")

            # Validate backbuffer
            if self.backbuffer is None:
                logger.error("CRITICAL: Backbuffer is None!")
                raise RuntimeError("Backbuffer not initialized")

            # Log detailed state before push
            logger.debug(f"Presenting: fb={self.fb}, bb_size={self.backbuffer.size}, fb_size=({self.fb.width},{self.fb.height})")

            # Push to framebuffer
            self.fb.push(self.backbuffer)

            logger.debug("Present completed successfully")

        except Exception as e:
            # Log detailed error with stack trace
            logger.error(f"CRITICAL: Failed to present to framebuffer: {e}", exc_info=True)
            logger.error(f"  Framebuffer: {self.fb}")
            logger.error(f"  Backbuffer: {self.backbuffer}")
            logger.error(f"  Backbuffer size: {self.backbuffer.size if self.backbuffer else 'None'}")

            # Re-raise to ensure caller knows about the error
            raise'''

    if old_present not in content:
        print("ERROR: Could not find the present() method to patch!")
        print("The file may have already been modified or have a different format.")
        return 1

    # Apply patch
    content = content.replace(old_present, new_present)

    # Write patched content
    print(f"Applying fix to: {RENDERER_FILE}")
    with open(RENDERER_FILE, 'w') as f:
        f.write(content)

    print("")
    print("SUCCESS! Fix applied.")
    print("")
    print("Changes made:")
    print("  1. Added validation for framebuffer and backbuffer references")
    print("  2. Added detailed debug logging before push")
    print("  3. Added detailed error logging with stack traces")
    print("  4. Changed behavior to re-raise exceptions instead of swallowing them")
    print("")
    print("To restore the original file:")
    print(f"  cp {BACKUP_FILE} {RENDERER_FILE}")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
