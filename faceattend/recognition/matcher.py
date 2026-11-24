"""1:N matching against enrolled employees/vendors, plus multi-frame voting."""
from collections import deque
from dataclasses import dataclass

import numpy as np

from ..config import Settings


@dataclass
class MatchResult:
    person_id: int | None  # None = nobody confident enough
    score: float
    runner_up: float
    accepted: bool


class Gallery:
    """person_id -> (n, d) array of L2-normalised embeddings (several poses each)."""

    def __init__(self, settings: Settings | None = None):
        self.s = settings or Settings()
        self._items: dict[int, np.ndarray] = {}

    def set_person(self, person_id: int, embeddings) -> None:
        arr = np.atleast_2d(np.asarray(embeddings, dtype=np.float32))
        arr = arr / (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)
        self._items[person_id] = arr

    def remove_person(self, person_id: int) -> None:
        self._items.pop(person_id, None)

    def __len__(self) -> int:
        return len(self._items)

    def _scores(self, emb: np.ndarray) -> dict[int, float]:
        emb = emb / (np.linalg.norm(emb) + 1e-9)
        return {pid: float((arr @ emb).max()) for pid, arr in self._items.items()}

    def identify(self, emb) -> MatchResult:
        scores = self._scores(np.asarray(emb, dtype=np.float32))
        if not scores:
            return MatchResult(None, 0.0, 0.0, False)
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_id, best = ranked[0]
        runner = ranked[1][1] if len(ranked) > 1 else 0.0
        ok = best >= self.s.match_threshold and (best - runner) >= self.s.match_margin
        return MatchResult(best_id if ok else None, best, runner, ok)

    def find_duplicate(self, emb, exclude_id: int | None = None) -> int | None:
        """Enrollment guard: does this face already belong to somebody else?"""
        scores = self._scores(np.asarray(emb, dtype=np.float32))
        scores.pop(exclude_id, None)
        if not scores:
            return None
        pid, sc = max(scores.items(), key=lambda kv: kv[1])
        return pid if sc >= self.s.duplicate_threshold else None


class VoteTracker:
    """Confirm an identity only when k of the last m frames agree (kills one-frame false matches)."""

    def __init__(self, k: int, m: int):
        self.k, self.recent = k, deque(maxlen=m)

    def push(self, person_id: int | None) -> int | None:
        self.recent.append(person_id)
        counts: dict[int, int] = {}
        for p in self.recent:
            if p is not None:
                counts[p] = counts.get(p, 0) + 1
        for p, c in counts.items():
            if c >= self.k:
                return p
        return None

    def reset(self) -> None:
        self.recent.clear()
