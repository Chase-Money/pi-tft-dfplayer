#!/usr/bin/env python3
"""
Unified entrypoint for the touchscreen application.

Uses ConfigV2 + TouchController + ScreenManagerV2 stack via app.Application.
"""

import logging

from app import Application


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    try:
        Application().run()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Exiting application")


if __name__ == "__main__":
    main()
