from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Passage:
    id: str
    title: str
    text: str


@dataclass(frozen=True)
class SessionConfig:
    timer_seconds: int | None


@dataclass
class SessionState:
    current_index: int
    typed_text: str
    error_count: int
    correct_count: int
    elapsed_ms: int
    is_complete: bool
    is_time_up: bool


@dataclass(frozen=True)
class SessionResult:
    gross_wpm: float
    net_wpm: float
    accuracy_pct: float
    total_chars: int
    correct_chars: int
    error_chars: int
    duration_sec: float

