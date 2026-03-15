from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RiftboundLogicalRecord:
    game_slug: str
    set_name: str
    set_code: str
    card_name: str
    card_external_id: str | None
    print_external_id: str | None
    collector_number: str
    rarity: str
    variant: str
    locale: str
    image_url: str | None
    thumbnail_url: str | None
    source_system: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiftboundBatch:
    sets: list[dict[str, Any]]
    cards: list[dict[str, Any]]
    prints: list[dict[str, Any]]


class RiftboundBackend:
    source_name = "unknown"

    def fetch_sets(self, **kwargs) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_cards(self, **kwargs) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_prints(self, **kwargs) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_all(self, **kwargs) -> RiftboundBatch:
        return RiftboundBatch(
            sets=self.fetch_sets(**kwargs),
            cards=self.fetch_cards(**kwargs),
            prints=self.fetch_prints(**kwargs),
        )

    def to_logical_records(self, batch: RiftboundBatch, **kwargs) -> list[RiftboundLogicalRecord]:
        raise NotImplementedError
