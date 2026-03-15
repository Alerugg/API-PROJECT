from __future__ import annotations

import os
import time
from typing import Any

import requests

from app.ingest.connectors.riftbound_types import RiftboundBackend, RiftboundBatch, RiftboundLogicalRecord


class RiftboundOfficialBackend(RiftboundBackend):
    source_name = "official"

    def __init__(self, logger):
        self.logger = logger
        self.base_url = (os.getenv("RIFTBOUND_API_BASE_URL") or "").strip().rstrip("/")
        self.api_key = (os.getenv("RIFTBOUND_API_KEY") or "").strip()
        self.timeout_seconds = max(float(os.getenv("RIFTBOUND_TIMEOUT_SECONDS") or 30), 1)
        self.session = requests.Session()
        headers = {
            "Accept": "application/json",
            "User-Agent": "API-PROJECT/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.session.headers.update(headers)

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _request_json(self, endpoint: str) -> list[dict[str, Any]]:
        if not self.base_url:
            raise RuntimeError("RIFTBOUND_API_BASE_URL is required for official Riftbound source")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        wait_seconds = 0.5
        retry_status = {429, 500, 502, 503, 504}
        last_error: Exception | None = None
        for attempt in range(1, 5):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                if response.status_code in retry_status:
                    self.logger.warning(
                        "ingest riftbound official_retry endpoint=%s attempt=%s status=%s wait_seconds=%s",
                        endpoint,
                        attempt,
                        response.status_code,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    wait_seconds *= 2
                    continue
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list):
                    return payload
                if isinstance(payload, dict):
                    return payload.get("data") or payload.get("results") or []
                return []
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= 4:
                    break
                time.sleep(wait_seconds)
                wait_seconds *= 2

        raise RuntimeError(f"Riftbound official request failed endpoint={endpoint} last_error={last_error}")

    def fetch_sets(self, **kwargs) -> list[dict[str, Any]]:
        return self._request_json("sets")

    def fetch_cards(self, **kwargs) -> list[dict[str, Any]]:
        return self._request_json("cards")

    def fetch_prints(self, **kwargs) -> list[dict[str, Any]]:
        prints = self._request_json("prints")
        limit = kwargs.get("limit")
        if limit:
            return prints[: int(limit)]
        return prints

    @staticmethod
    def _pick_primary_image(payload: dict[str, Any]) -> tuple[str | None, str | None]:
        image_candidates = [
            payload.get("image_url"),
            payload.get("image"),
            payload.get("art_url"),
            payload.get("image_uri"),
            (payload.get("images") or {}).get("large") if isinstance(payload.get("images"), dict) else None,
            (payload.get("images") or {}).get("normal") if isinstance(payload.get("images"), dict) else None,
            (payload.get("images") or {}).get("small") if isinstance(payload.get("images"), dict) else None,
        ]
        images_list = payload.get("images") if isinstance(payload.get("images"), list) else []
        for item in images_list:
            if isinstance(item, dict):
                image_candidates.append(item.get("url") or item.get("large") or item.get("normal"))

        primary = next((str(url).strip() for url in image_candidates if str(url or "").strip()), None)
        thumbnail = None
        thumb_candidates = [
            payload.get("thumbnail_url"),
            payload.get("thumb_url"),
            (payload.get("images") or {}).get("small") if isinstance(payload.get("images"), dict) else None,
        ]
        thumbnail = next((str(url).strip() for url in thumb_candidates if str(url or "").strip()), None)
        return primary, thumbnail

    def to_logical_records(self, batch: RiftboundBatch, **kwargs) -> list[RiftboundLogicalRecord]:
        set_map: dict[str, dict[str, Any]] = {}
        for set_payload in batch.sets:
            set_id = str(set_payload.get("id") or set_payload.get("set_id") or set_payload.get("code") or "").strip()
            if set_id:
                set_map[set_id] = set_payload

        card_map: dict[str, dict[str, Any]] = {}
        for card_payload in batch.cards:
            card_id = str(card_payload.get("id") or card_payload.get("card_id") or card_payload.get("external_id") or "").strip()
            if card_id:
                card_map[card_id] = card_payload

        logical: list[RiftboundLogicalRecord] = []
        for print_payload in batch.prints:
            set_payload = set_map.get(str(print_payload.get("set_id") or print_payload.get("set_code") or "").strip(), {})
            card_payload = card_map.get(str(print_payload.get("card_id") or print_payload.get("card_external_id") or "").strip(), {})
            primary, thumb = self._pick_primary_image(print_payload)
            logical.append(
                RiftboundLogicalRecord(
                    game_slug="riftbound",
                    set_name=str(set_payload.get("name") or print_payload.get("set_name") or "").strip(),
                    set_code=str(set_payload.get("code") or print_payload.get("set_code") or "").strip(),
                    card_name=str(card_payload.get("name") or print_payload.get("card_name") or "").strip(),
                    card_external_id=str(card_payload.get("id") or print_payload.get("card_id") or "").strip() or None,
                    print_external_id=str(print_payload.get("id") or print_payload.get("print_id") or "").strip() or None,
                    collector_number=str(print_payload.get("collector_number") or "").strip(),
                    rarity=str(print_payload.get("rarity") or "").strip(),
                    variant=str(print_payload.get("variant") or "").strip(),
                    locale=str(print_payload.get("locale") or print_payload.get("language") or "").strip(),
                    image_url=primary,
                    thumbnail_url=thumb,
                    source_system="riot_content_api",
                    metadata={
                        "set_external_id": set_payload.get("id"),
                        "raw_print": {
                            "id": print_payload.get("id"),
                            "set_id": print_payload.get("set_id"),
                            "card_id": print_payload.get("card_id"),
                        },
                    },
                )
            )
        return logical
