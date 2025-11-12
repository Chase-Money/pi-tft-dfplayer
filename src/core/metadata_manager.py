"""
Metadata and artwork management for the DFPlayer GUI.
"""

import os
import json
from PIL import Image

class MetadataManager:
    def __init__(self, config):
        self.config = config
        self.metadata = self._load_metadata()
        self.artwork_cache = {}

    def _load_metadata(self):
        """Load track metadata from a JSON file."""
        metadata_path = self.config.get_metadata_path()
        if not metadata_path or not os.path.exists(metadata_path):
            return {}

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            
            tracks = loaded_data.get("tracks", {})
            parsed_metadata = {}
            for key, info in tracks.items():
                try:
                    track_no = int(key)
                    parsed_metadata[track_no] = {
                        "title": info.get("title"),
                        "artist": info.get("artist"),
                        "artwork": info.get("artwork"),
                    }
                except (ValueError, TypeError):
                    continue
            return parsed_metadata
        except Exception:
            return {}

    def get_metadata(self, track_number):
        """Get metadata for a specific track."""
        return self.metadata.get(track_number, {})

    def get_artwork(self, track_number, size):
        """Get artwork for a specific track, resizing and caching it."""
        meta = self.get_metadata(track_number)
        art_path = meta.get("artwork")
        if not art_path:
            return None

        if art_path in self.artwork_cache:
            return self.artwork_cache[art_path]

        artwork_root = self.config.get_artwork_root()
        if artwork_root and not os.path.isabs(art_path):
            art_path = os.path.join(artwork_root, art_path)

        if not os.path.exists(art_path):
            return None

        try:
            with Image.open(art_path) as img:
                img = img.convert("RGB")
                img.thumbnail(size, Image.LANCZOS)
                
                # Create a new image with a background and paste the thumbnail
                canvas = Image.new("RGB", size, (35, 35, 40))
                ox = (canvas.width - img.width) // 2
                oy = (canvas.height - img.height) // 2
                canvas.paste(img, (ox, oy))

                self.artwork_cache[art_path] = canvas
                return canvas
        except Exception:
            return None
