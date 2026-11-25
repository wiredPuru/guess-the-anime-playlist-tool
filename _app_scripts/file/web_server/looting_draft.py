"""Rules and media selection for a single live anime draft."""

import random
import time
from math import ceil
from uuid import uuid4


THEME_WEIGHTS = {"OP": 60, "ED": 30, "IN": 10}
BIN_COUNT = 3
MIN_TARGET_CHOICES = 200


def library_pool():
    """Group available, filtered themes by anime, collapsing video versions."""
    from core.game_state import state
    from _app_scripts.file.metadata import metadata_fetch
    from _app_scripts.playlists import filters, infinite, playlist

    active_filter = state.metadata.playlist.get("filter")
    files = infinite.get_infinite_directory_files()
    if active_filter:
        files = filters.evaluate_filter({**active_filter, "theme_type": "All"}, files)
    shows = {}
    for filename in playlist.deduplicate_theme_versions(files):
        theme = metadata_fetch.get_file_metadata_by_name(filename) or {}
        mal_id = theme.get("mal")
        kind = str(theme.get("slug") or "").upper()[:2]
        if not mal_id or kind not in THEME_WEIGHTS:
            continue
        anime = state.metadata.anime_metadata.get(mal_id) or {}
        if anime.get("igdb") or theme.get("igdb"):
            continue
        title = anime.get("title_english") or anime.get("title") or theme.get("title")
        if title:
            _, tracks = shows.setdefault(str(mal_id), (title, {}))
            tracks.setdefault(kind, []).append(filename)
    return list(shows.values())


class LootingDraft:
    """Mutable draft state. The web server serializes calls with its draft lock."""

    def __init__(self, roster, picks, seconds, pool):
        self.id = uuid4().hex
        self.roster = roster
        self.picks = picks
        self.slots = len(roster) * picks
        if not self.slots:
            raise ValueError("At least one named player must join before starting.")
        if len(pool) < self.slots:
            raise ValueError(
                f"This draft needs {self.slots} playable anime. The current pool has {len(pool)}."
            )
        board_size = min(len(pool), max(MIN_TARGET_CHOICES, self.slots + (self.slots + 1) // 2))
        self.cards = random.sample(pool, board_size)
        self.owners = {}
        self.inspections = {}
        self.deadline = time.monotonic() + seconds
        self.finished = None
        self.auto_filled = 0

    def remaining_ms(self):
        return max(0, ceil((self.deadline - time.monotonic()) * 1000))

    def change(self, player, action, target):
        if self.finished is not None or time.monotonic() >= self.deadline:
            raise ValueError("The draft has closed.")
        if action == "inspect" and target == -1:
            self.inspections.pop(player, None)
        elif action == "inspect" and 0 <= target < len(self.cards):
            self.inspections[player] = target
        elif action == "release" and self.owners.get(target) == player:
            del self.owners[target]
        elif action == "claim" and 0 <= target < len(self.cards):
            if target in self.owners:
                raise ValueError("Someone already claimed that anime.")
            if list(self.owners.values()).count(player) >= self.picks:
                raise ValueError("Release a pick to make room.")
            self.owners[target] = player
        else:
            raise ValueError("That pick is no longer available to you.")

    def view(self, player, online, host=False):
        summary = {
            "id": self.id, "slots": self.slots, "claimed": len(self.owners),
            "remaining": self.remaining_ms(), "host": host,
            "ready": self.finished is not None, "autoFilled": self.auto_filled,
        }
        if self.finished is not None or player is None:
            return summary
        inspected = self.inspections.get(player)
        return {
            **summary,
            "inspected": inspected,
            "players": len(online),
            "limit": self.picks,
            "picks": [{"id": i, "title": self.cards[i][0]}
                      for i, owner in self.owners.items() if owner == player],
            "bins": [
                [self._sleeve_view(i, player, inspected)
                 for i in range(bin_index, len(self.cards), BIN_COUNT)]
                for bin_index in range(BIN_COUNT)
            ],
        }

    def _sleeve_view(self, card, player, inspected):
        owner = self.owners.get(card)
        own_pick = owner == player
        selected = card == inspected
        return {
            "id": card,
            "title": self.cards[card][0] if selected and (owner is None or own_pick) else None,
            "taken": owner is not None and (selected or own_pick),
        }

    def finish(self):
        if self.finished is None:
            self.auto_filled = self.slots - len(self.owners)
            unclaimed = [i for i in range(len(self.cards)) if i not in self.owners]
            selected = list(self.owners) + random.sample(unclaimed, self.auto_filled)
            random.shuffle(selected)
            self.finished = []
            for card in selected:
                tracks = self.cards[card][1]
                kind = random.choices(list(tracks), [THEME_WEIGHTS[k] for k in tracks])[0]
                self.finished.append({
                    "filename": random.choice(tracks[kind]),
                    "looting_effect": random.choice(("blur", "pixelize")),
                    "looted_by": self.roster.get(self.owners.get(card)),
                })
        return self.finished
