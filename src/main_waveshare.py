#!/usr/bin/env python3
"""
Main entry point for the Waveshare 1.44" LCD HAT variant.
"""
import sys

from app_waveshare import ApplicationWaveshare

def main():
    """Initializes and runs the Waveshare application variant."""
    app = None
    try:
        app = ApplicationWaveshare()
        app.run()
    except KeyboardInterrupt:
        print("\nExiting application.")
    except Exception as e:
        print(f"\nAn unhandled exception occurred: {e}")
        # In a real scenario, you might want to log this to a file
        sys.exit(1)
    finally:
        if app:
            app.cleanup()

if __name__ == "__main__":
    main()
