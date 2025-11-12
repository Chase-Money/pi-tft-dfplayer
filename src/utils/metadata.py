"""Metadata and artwork loading utilities.

Handles JSON metadata parsing and album artwork loading/caching.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from PIL import Image

logger = logging.getLogger(__name__)


def load_metadata(metadata_path: str, artwork_root: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
    """Load track metadata from JSON file.

    Args:
        metadata_path: Path to metadata JSON file
        artwork_root: Root directory for relative artwork paths

    Returns:
        dict: Mapping of track numbers to metadata dicts
    """
    if not os.path.exists(metadata_path):
        logger.warning(f"Metadata file not found: {metadata_path}")
        return {}

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        # Handle both {"tracks": {...}} and {...} formats
        tracks_data = loaded.get("tracks") if isinstance(loaded, dict) and "tracks" in loaded else loaded

        if not isinstance(tracks_data, dict):
            logger.error("Invalid metadata format")
            return {}

        # Determine base directory for artwork
        if artwork_root:
            base_dir = artwork_root
        elif os.path.isdir(metadata_path):
            base_dir = metadata_path
        else:
            base_dir = os.path.dirname(metadata_path) or "."

        # Parse metadata
        metadata = {}
        for key, info in tracks_data.items():
            try:
                track_no = int(key)
            except ValueError:
                logger.warning(f"Invalid track number in metadata: {key}")
                continue

            if not isinstance(info, dict):
                info = {}

            entry = {
                "title": info.get("title"),
                "artist": info.get("artist"),
                "artwork": None,
            }

            # Resolve artwork path
            art_path = info.get("artwork")
            if art_path:
                if not os.path.isabs(art_path):
                    # Normalize path to prevent traversal attacks
                    art_path = os.path.normpath(art_path)
                    # Ensure the normalized path doesn't attempt to escape base_dir
                    if art_path.startswith('..') or os.path.isabs(art_path):
                        logger.warning(f"Rejected potentially unsafe artwork path: {art_path}")
                        entry["artwork"] = None
                    else:
                        entry["artwork"] = os.path.join(base_dir, art_path)
                else:
                    entry["artwork"] = art_path

            metadata[track_no] = entry

        logger.info(f"Loaded metadata for {len(metadata)} tracks")
        return metadata

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in metadata file: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
        return {}


def load_artwork_thumbnail(artwork_path: str, size=(200, 200)) -> Optional[Image.Image]:
    """Load and resize artwork image.

    Args:
        artwork_path: Path to artwork image
        size: Target thumbnail size (width, height)

    Returns:
        PIL Image: Thumbnail or None if failed
    """
    if not artwork_path or not os.path.exists(artwork_path):
        return None

    try:
        with Image.open(artwork_path) as img:
            img = img.convert("RGB")
            thumb = img.copy()
            thumb.thumbnail(size, Image.LANCZOS)

        # Center on canvas
        canvas = Image.new("RGB", size, (35, 35, 40))
        offset_x = (canvas.width - thumb.width) // 2
        offset_y = (canvas.height - thumb.height) // 2
        canvas.paste(thumb, (offset_x, offset_y))

        logger.debug(f"Loaded artwork thumbnail: {artwork_path}")
        return canvas

    except Exception as e:
        logger.error(f"Failed to load artwork {artwork_path}: {e}")
        return None


class ArtworkCache:
    """LRU cache for artwork thumbnails.

    Attributes:
        max_size: Maximum number of cached thumbnails
        cache: Cached artwork dictionary
    """

    def __init__(self, max_size=10):
        """Initialize artwork cache.

        Args:
            max_size: Maximum cache size
        """
        self.max_size = max_size
        self.cache: Dict[str, Optional[Image.Image]] = {}
        self._access_order = []

    def get(self, artwork_path: str, size=(200, 200)) -> Optional[Image.Image]:
        """Get artwork thumbnail from cache or load it.

        Args:
            artwork_path: Path to artwork file
            size: Thumbnail size

        Returns:
            PIL Image: Thumbnail or None
        """
        if artwork_path in self.cache:
            # Move to end (most recently used)
            if artwork_path in self._access_order:
                self._access_order.remove(artwork_path)
            self._access_order.append(artwork_path)

            logger.debug(f"Artwork cache hit: {artwork_path}")
            return self.cache[artwork_path]

        # Load thumbnail
        thumbnail = load_artwork_thumbnail(artwork_path, size)

        # Add to cache
        self.cache[artwork_path] = thumbnail
        self._access_order.append(artwork_path)

        # Evict oldest if over limit
        while len(self.cache) > self.max_size:
            oldest = self._access_order.pop(0)
            del self.cache[oldest]
            logger.debug(f"Evicted from artwork cache: {oldest}")

        return thumbnail

    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self._access_order.clear()
        logger.info("Artwork cache cleared")
