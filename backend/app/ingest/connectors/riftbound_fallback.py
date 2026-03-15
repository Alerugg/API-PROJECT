from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from app.ingest.connectors.riftbound_types import RiftboundBackend, RiftboundBatch, RiftboundLogicalRecord


class RiftboundFallbackBackend(RiftboundBackend):
    source_name = "fallback"

    def __init__(self, logger):
        self.logger = logger
        self.base_url = (os.getenv("RIFTBOUND_FALLBACK_BASE_URL") or "").strip().rstrip("/")
        self.timeout_seconds = max(float(os.getenv("RIFTBOUND_TIMEOUT_SECONDS") or 30), 1)

    def _resolve_fixture_path(self, path: str | Path | None) -> Path:
        fixture_name = "riftbound_sample.json"
        root = Path(__file__).resolve().parents[3]
        candidate = Path(path) if path else root / "data" / "fixtures" / fixture_name
        if candidate.is_file():
            return candidate
        for option in (root / str(candidate), root.parent / str(candidate), root / "data" / "fixtures" / fixture_name):
            if option.is_file():
                return option
            if option.is_dir() and (option / fixture_name).is_file():
                return option / fixture_name
        raise ValueError(f"Unable to resolve Riftbound fixture path: {path}")

    def _load_fixture_batch(self, path: str | Path | None = None) -> RiftboundBatch:
        payload = json.loads(self._resolve_fixture_path(path).read_text(encoding="utf-8"))
        return RiftboundBatch(
            sets=payload.get("sets") or [],
            cards=payload.get("cards") or [],
            prints=payload.get("prints") or [],
        )

    def _request_json(self, endpoint: str) -> list[dict[str, Any]]:
        if not self.base_url:
            raise RuntimeError("RIFTBOUND_FALLBACK_BASE_URL is required for remote fallback mode")
        response = requests.get(f"{self.base_url}/{endpoint.lstrip('/')}", timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return payload.get("data") or payload.get("results") or []
        return []

    def fetch_sets(self, **kwargs) -> list[dict[str, Any]]:
        if kwargs.get("fixture", False):
            return self._load_fixture_batch(kwargs.get("path")).sets
        return self._request_json("sets")

    def fetch_cards(self, **kwargs) -> list[dict[str, Any]]:
        if kwargs.get("fixture", False):
            return self._load_fixture_batch(kwargs.get("path")).cards
        return self._request_json("cards")

    def fetch_prints(self, **kwargs) -> list[dict[str, Any]]:
        if kwargs.get("fixture", False):
            prints = self._load_fixture_batch(kwargs.get("path")).prints
        else:
            prints = self._request_json("prints")
        limit = kwargs.get("limit")
        if limit:
            return prints[: int(limit)]
        return prints

    def fetch_all(self, **kwargs) -> RiftboundBatch:
        if kwargs.get("fixture", False):
            return self._load_fixture_batch(kwargs.get("path"))
        return super().fetch_all(**kwargs)

    def to_logical_records(self, batch: RiftboundBatch, **kwargs) -> list[RiftboundLogicalRecord]:
        sets = {str(item.get("id") or item.get("code") or "").strip(): item for item in batch.sets}
        cards = {str(item.get("id") or item.get("name") or "").strip(): item for item in batch.cards}

        seen_print_ids: set[str] = set()
        logical: list[RiftboundLogicalRecord] = []
        for print_item in batch.prints:
            print_id = str(print_item.get("id") or "").strip()
            if print_id and print_id in seen_print_ids:
                continue
            if print_id:
                seen_print_ids.add(print_id)

            set_payload = sets.get(str(print_item.get("set_id") or print_item.get("set_code") or "").strip(), {})
            card_payload = cards.get(str(print_item.get("card_id") or print_item.get("card_name") or "").strip(), {})

            logical.append(
                RiftboundLogicalRecord(
                    game_slug="riftbound",
                    set_name=str(set_payload.get("name") or print_item.get("set_name") or "").strip(),
                    set_code=str(set_payload.get("code") or print_item.get("set_code") or "").strip(),
                    card_name=str(card_payload.get("name") or print_item.get("card_name") or "").strip(),
                    card_external_id=str(card_payload.get("id") or print_item.get("card_id") or "").strip() or None,
                    print_external_id=print_id or None,
                    collector_number=str(print_item.get("collector_number") or "").strip(),
                    rarity=str(print_item.get("rarity") or "").strip(),
                    variant=str(print_item.get("variant") or "").strip(),
                    locale=str(print_item.get("locale") or print_item.get("language") or "").strip(),
                    image_url=(print_item.get("primary_image_url") or print_item.get("image_url") or None),
                    thumbnail_url=(print_item.get("thumbnail_url") or None),
                    source_system="riftcodex",
                    metadata={
                        "set_external_id": set_payload.get("id"),
                        "raw_print": {
                            "id": print_item.get("id"),
                            "set_id": print_item.get("set_id"),
                            "card_id": print_item.get("card_id"),
                        },
                    },
                )
            )
        return logical
