"""Metadata and artwork loading utilities.

Handles JSON metadata parsing and album artwork loading/caching.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

logger = logging.getLogger(__name__)


def _validate_artwork_path(artwork_path: str, base_dir: str) -> Optional[str]:
    """
    Validate and resolve artwork path to prevent directory traversal attacks.

    This function provides security against path traversal by:
    - Rejecting paths with suspicious characters (null bytes, control chars)
    - Resolving symlinks to detect traversal attempts
    - Ensuring relative paths stay within base_dir
    - Validating absolute paths against allowed prefixes

    Args:
        artwork_path: Raw artwork path from metadata (relative or absolute)
        base_dir: Base directory for relative paths

    Returns:
        Validated absolute path, or None if path is unsafe

    Examples:
        >>> _validate_artwork_path("artwork.jpg", "/boot/music/")
        '/boot/music/artwork.jpg'
        >>> _validate_artwork_path("../../etc/passwd", "/boot/music/")
        None
    """
    if not artwork_path or not isinstance(artwork_path, str):
        return None

    try:
        # Reject paths with suspicious characters
        suspicious_patterns = [
            r'\x00',  # Null bytes
            r'[\x01-\x1f]',  # Control characters (excluding newline for safety)
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, artwork_path):
                logger.warning(f"Artwork path contains suspicious characters: {artwork_path}")
                return None

        # Resolve to absolute path using pathlib (resolves symlinks)
        if os.path.isabs(artwork_path):
            # Absolute path - resolve and validate
            resolved = Path(artwork_path).resolve()
            resolved_str = str(resolved)

            # For absolute paths, ensure they're in common safe directories
            allowed_absolute_prefixes = ["/boot/", "/home/", "/media/", "/mnt/"]
            path_is_safe = any(
                resolved_str.startswith(prefix) for prefix in allowed_absolute_prefixes
            )

            if not path_is_safe:
                logger.warning(
                    f"Absolute artwork path outside allowed directories: {artwork_path} -> {resolved_str}"
                )
                return None

            logger.debug(f"Validated absolute artwork path: {resolved_str}")
            return resolved_str

        # Relative path - must stay within base_dir
        # First check for obvious traversal attempts
        if artwork_path.startswith('..') or '/../' in artwork_path or artwork_path.endswith('/..'):
            logger.warning(f"Path traversal attempt detected: {artwork_path}")
            return None

        # Resolve relative to base_dir
        base_path = Path(base_dir).resolve()
        full_path = (base_path / artwork_path).resolve()
        full_path_str = str(full_path)

        # Ensure resolved path is within base_dir (using pathlib.is_relative_to would be cleaner in Python 3.9+)
        base_str = str(base_path)
        if not base_str.endswith(os.sep):
            base_str += os.sep

        # Check if resolved path is within base directory
        if not (full_path_str.startswith(base_str) or full_path_str == str(base_path)):
            logger.warning(
                f"Relative artwork path escapes base directory:\n"
                f"  Input: {artwork_path}\n"
                f"  Base: {base_dir}\n"
                f"  Resolved: {full_path_str}"
            )
            return None

        logger.debug(f"Validated relative artwork path: {artwork_path} -> {full_path_str}")
        return full_path_str

    except Exception as e:
        logger.error(f"Error validating artwork path {artwork_path}: {e}")
        return None


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

            # Resolve artwork path with security validation
            art_path = info.get("artwork")
            if art_path:
                validated_path = _validate_artwork_path(art_path, base_dir)
                if validated_path:
                    entry["artwork"] = validated_path
                else:
                    logger.warning(f"Rejected unsafe artwork path: {art_path}")
                    entry["artwork"] = None

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
