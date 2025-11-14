#!/usr/bin/env python3
"""
Main entry point for the v3 application using the v2 UI framework.
"""
import sys
import os

# Ensure the source directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app_v2 import Application

def main():
    """Initializes and runs the application."""
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt:
        print("\nExiting application.")
    except Exception as e:
        print(f"\nAn unhandled exception occurred: {e}")
        # In a real scenario, you might want to log this to a file
        sys.exit(1)

if __name__ == "__main__":
    main()

