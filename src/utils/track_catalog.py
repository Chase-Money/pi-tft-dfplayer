"""Track catalog loading utilities.

Handles loading track catalog from text files.
"""

import logging
import os
from typing import List, Optional

from core.state import Track

logger = logging.getLogger(__name__)


def load_track_catalog(catalog_path: Optional[str] = None, fallback_count=30) -> List[Track]:
    """Load track catalog from file.

    Searches for catalog file in multiple locations:
    1. Explicit catalog_path (if provided)
    2. ../config/track_catalog.txt (relative to src/)
    3. /home/pi/dfplayer_tracks.txt

    File format (one track per line):
    - "number|title" format (preferred)
    - "number title" format (space-separated)
    - Lines starting with # are comments

    Args:
        catalog_path: Explicit path to catalog file (optional)
        fallback_count: Number of placeholder tracks if no catalog found

    Returns:
        list: List of Track objects
    """
    # Build search paths
    search_paths = []

    if catalog_path:
        search_paths.append(catalog_path)

    # Add default search locations
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    search_paths.extend([
        os.path.join(base_dir, "config", "track_catalog.txt"),
        "/home/pi/dfplayer_tracks.txt",
    ])

    # Try each path
    for path in search_paths:
        if not path:
            continue

        try:
            if not os.path.exists(path):
                continue
        except Exception:
            continue

        tracks = _parse_catalog_file(path)
        if tracks:
            logger.info(f"Loaded {len(tracks)} tracks from {path}")
            return tracks

    # Fallback: generate placeholder tracks
    logger.warning(f"No track catalog found, generating {fallback_count} placeholder tracks")
    return [
        Track(number=i + 1, title=f"Track {i + 1:03d}")
        for i in range(fallback_count)
    ]


def _parse_catalog_file(path: str) -> List[Track]:
    """Parse track catalog file.

    Args:
        path: Path to catalog file

    Returns:
        list: List of Track objects or empty list if parsing fails
    """
    tracks = []

    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse line
                try:
                    track = _parse_catalog_line(line)
                    if track:
                        tracks.append(track)
                except Exception as e:
                    logger.warning(f"Error parsing line {line_num} in {path}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Failed to read catalog file {path}: {e}")
        return []

    if tracks:
        # Sort by track number
        tracks.sort(key=lambda t: t.number)

    return tracks


def _parse_catalog_line(line: str) -> Optional[Track]:
    """Parse single catalog line.

    Args:
        line: Catalog line

    Returns:
        Track: Track object or None if invalid
    """
    # Try pipe-separated format first
    if "|" in line:
        num_str, title = line.split("|", 1)
        num_str = num_str.strip()
        title = title.strip()
    else:
        # Try space-separated format
        parts = line.split(None, 1)
        if not parts:
            return None

        num_str = parts[0]
        title = parts[1].strip() if len(parts) > 1 else ""

    # Parse track number
    try:
        track_no = int(num_str, 10)
    except ValueError:
        logger.warning(f"Invalid track number: {num_str}")
        return None

    # Default title if empty
    if not title:
        title = f"Track {track_no:03d}"

    return Track(number=track_no, title=title)
