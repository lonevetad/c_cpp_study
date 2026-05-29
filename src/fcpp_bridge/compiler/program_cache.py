import hashlib
from pathlib import Path
from typing import Dict, Optional


class ProgramCache:
    """Cache compiled programs by content hash."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest: Dict[str, Path] = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Path]:
        """Load cache manifest from disk."""
        manifest_path = self.cache_dir / ".cache_manifest"
        manifest = {}
        if manifest_path.exists():
            for line in manifest_path.read_text().strip().split("\n"):
                if line and ":" in line:
                    key, path = line.split(":", 1)
                    manifest[key] = Path(path)
        return manifest

    def _save_manifest(self) -> None:
        """Save cache manifest to disk."""
        manifest_path = self.cache_dir / ".cache_manifest"
        lines = [f"{k}:{v}" for k, v in self.manifest.items()]
        manifest_path.write_text("\n".join(lines))

    def _hash(self, content: str) -> str:
        """Hash C++ code to generate unique ID."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def lookup(self, cpp_code: str) -> Optional[Path]:
        """Return cached binary path (None if not in manifest)."""
        cache_key = self._hash(cpp_code)
        return self.manifest.get(cache_key)

    def store(self, cpp_code: str, binary_path: Path) -> None:
        """Cache binary path for this code."""
        cache_key = self._hash(cpp_code)
        self.manifest[cache_key] = binary_path
        self._save_manifest()

    def get_key(self, cpp_code: str) -> str:
        """Get cache key for code (for filename generation)."""
        return self._hash(cpp_code)
