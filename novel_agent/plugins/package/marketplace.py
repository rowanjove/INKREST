"""Marketplace client and repository index models for Inkrest Plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from novel_agent.plugins.package.verifier import compute_package_hash, verify_package


@dataclass
class MarketplaceItem:
    """Represents a plugin available in the marketplace index."""
    id: str
    name: str
    version: str
    display_name: str
    description: str = ""
    author: str = ""
    plugin_type: str = "pipeline_hook"
    download_url: str = ""
    hash: str = ""
    signature: str = ""
    capabilities: List[str] = field(default_factory=list)
    engines: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarketplaceItem:
        return cls(
            id=data.get("id") or data.get("name") or "",
            name=data.get("name") or data.get("id") or "",
            version=data.get("version", "0.1.0"),
            display_name=data.get("display_name") or data.get("id") or "",
            description=data.get("description", ""),
            author=data.get("author", ""),
            plugin_type=data.get("plugin_type", "pipeline_hook"),
            download_url=data.get("download_url", ""),
            hash=data.get("hash", ""),
            signature=data.get("signature", ""),
            capabilities=data.get("capabilities", []),
            engines=data.get("engines", {}),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type,
            "download_url": self.download_url,
            "hash": self.hash,
            "signature": self.signature,
            "capabilities": self.capabilities,
            "engines": self.engines,
            "tags": self.tags,
        }


class MarketplaceClient:
    """Client for discovering, searching, and verifying remote plugins."""

    def __init__(self, registry_source: Optional[Dict[str, Any]] = None) -> None:
        self._items: Dict[str, MarketplaceItem] = {}
        if registry_source:
            self.load_registry_data(registry_source)

    def load_registry_file(self, index_file: Path) -> None:
        """Load registry from a local JSON file."""
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")
        content = json.loads(index_file.read_text(encoding="utf-8"))
        self.load_registry_data(content)

    def load_remote_registry(self, registry_url: str, timeout: float = 10.0) -> None:
        """Load registry index from a remote HTTP/HTTPS URL."""
        import urllib.request
        req = urllib.request.Request(registry_url, headers={"User-Agent": "Inkrest-Plugin-Client/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = json.loads(resp.read().decode("utf-8"))
            self.load_registry_data(content)

    def load_registry_data(self, data: Dict[str, Any]) -> None:
        """Load items from parsed index JSON."""
        plugins = data.get("plugins", [])
        self._items.clear()
        for p in plugins:
            item = MarketplaceItem.from_dict(p)
            self._items[item.id] = item

    def list_items(self) -> List[MarketplaceItem]:
        return list(self._items.values())

    def get_item(self, plugin_id: str) -> Optional[MarketplaceItem]:
        return self._items.get(plugin_id)

    def search(self, query: str = "", tag: Optional[str] = None) -> List[MarketplaceItem]:
        """Search plugins by keyword in id, display_name, description, or tag."""
        q = query.lower().strip()
        results: List[MarketplaceItem] = []
        for item in self._items.values():
            if tag and tag.lower() not in [t.lower() for t in item.tags]:
                continue
            if not q:
                results.append(item)
                continue
            match = (
                q in item.id.lower()
                or q in item.display_name.lower()
                or q in item.description.lower()
                or any(q in t.lower() for t in item.tags)
            )
            if match:
                results.append(item)
        return results

    def verify_package_data(
        self,
        package_bytes: bytes,
        item: MarketplaceItem,
        secret_key: Optional[str] = None,
    ) -> bool:
        """Verify hash and optional signature of downloaded package bytes."""
        if item.hash:
            actual_hash = compute_package_hash(package_bytes)
            if actual_hash.lower() != item.hash.lower():
                return False

        if item.signature and secret_key:
            if not verify_package(package_bytes, item.signature, secret_key):
                return False

        return True
