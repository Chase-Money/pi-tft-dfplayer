#!/usr/bin/env python3
"""
Unified entrypoint for the v2 touchscreen application.

Uses ConfigV2 + TouchController + ScreenManagerV2 stack via app_v2.Application.
"""

import logging

from app_v2 import Application


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
