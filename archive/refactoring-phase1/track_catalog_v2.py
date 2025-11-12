"""Track catalog loading utilities (v2).

Absolute import fix to avoid parent-relative import errors when used as a top-level package.
"""

import logging
import os
from typing import List, Optional

from core.state import Track

logger = logging.getLogger(__name__)


def load_track_catalog(catalog_path: Optional[str] = None, fallback_count=30) -> List[Track]:
    """Load track catalog from file.

    Search order:
    1. Explicit catalog_path
    2. ../config/track_catalog.txt (relative to repo root)
    3. /home/pi/dfplayer_tracks.txt
    """
    search_paths = []
    if catalog_path:
        search_paths.append(catalog_path)

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    search_paths.extend([
        os.path.join(base_dir, "config", "track_catalog.txt"),
        "/home/pi/dfplayer_tracks.txt",
    ])

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

    logger.warning(f"No track catalog found, generating {fallback_count} placeholder tracks")
    return [Track(number=i + 1, title=f"Track {i + 1:03d}") for i in range(fallback_count)]


def _parse_catalog_file(path: str) -> List[Track]:
    tracks: List[Track] = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    track = _parse_catalog_line(line)
                    if track:
                        tracks.append(track)
                except Exception as e:
                    logger.warning(f"Error parsing line {line_num} in {path}: {e}")
    except Exception as e:
        logger.error(f"Failed to read catalog file {path}: {e}")
        return []
    if tracks:
        tracks.sort(key=lambda t: t.number)
    return tracks


def _parse_catalog_line(line: str) -> Optional[Track]:
    if '|' in line:
        num_str, title = line.split('|', 1)
        num_str, title = num_str.strip(), title.strip()
    else:
        parts = line.split(None, 1)
        if not parts:
            return None
        num_str = parts[0]
        title = parts[1].strip() if len(parts) > 1 else ""
    try:
        track_no = int(num_str, 10)
    except ValueError:
        logger.warning(f"Invalid track number: {num_str}")
        return None
    if not title:
        title = f"Track {track_no:03d}"
    return Track(number=track_no, title=title)

