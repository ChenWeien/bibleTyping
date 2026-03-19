from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from typing_app.models import SessionConfig, SessionResult, SessionState


@dataclass
class TypingStats:
    correct_count: int
    error_count: int
    total_typed: int


def calculate_typing_stats(target_text: str, typed_text: str) -> TypingStats:
    limit = min(len(target_text), len(typed_text))
    correct = 0
    for idx in range(limit):
        if typed_text[idx] == target_text[idx]:
            correct += 1

    mismatches = limit - correct
    extras = max(0, len(typed_text) - len(target_text))
    errors = mismatches + extras
    return TypingStats(correct_count=correct, error_count=errors, total_typed=len(typed_text))


def compute_result(correct_chars: int, error_chars: int, duration_sec: float) -> SessionResult:
    safe_duration = max(duration_sec, 1e-9)
    minutes = safe_duration / 60.0
    gross_wpm = (correct_chars + error_chars) / 5.0 / minutes
    net_wpm = max(0.0, (correct_chars - error_chars) / 5.0 / minutes)
    total = correct_chars + error_chars
    accuracy_pct = (correct_chars / total * 100.0) if total else 100.0
    return SessionResult(
        gross_wpm=round(gross_wpm, 2),
        net_wpm=round(net_wpm, 2),
        accuracy_pct=round(accuracy_pct, 2),
        total_chars=total,
        correct_chars=correct_chars,
        error_chars=error_chars,
        duration_sec=round(safe_duration, 2),
    )


class TypingSession:
    def __init__(self, target_text: str, config: SessionConfig) -> None:
        self.target_text = target_text
        self.config = config
        self._started_at: float | None = None
        self._paused_started_at: float | None = None
        self._paused_total_ms = 0
        self.state = SessionState(
            current_index=0,
            typed_text="",
            error_count=0,
            correct_count=0,
            elapsed_ms=0,
            is_running=False,
            is_complete=False,
            is_time_up=False,
        )

    def start(self) -> None:
        self._started_at = None
        self._paused_started_at = None
        self._paused_total_ms = 0
        self.state.is_running = False
        self.state.elapsed_ms = 0
        self._update_time()

    def begin_timing(self) -> None:
        if self.state.is_complete or self.state.is_time_up or self.state.is_running:
            return
        if self._started_at is None:
            self._started_at = monotonic()
            self._paused_started_at = None
            self._paused_total_ms = 0
        elif self._paused_started_at is not None:
            paused_ms = int((monotonic() - self._paused_started_at) * 1000)
            self._paused_total_ms += max(0, paused_ms)
            self._paused_started_at = None
        self.state.is_running = True
        self._update_time()

    def update_typed_text(self, typed_text: str) -> SessionState:
        self._update_time()
        if self.state.is_complete or self.state.is_time_up:
            return self.state

        stats = calculate_typing_stats(self.target_text, typed_text)
        self.state.typed_text = typed_text
        self.state.current_index = len(typed_text)
        self.state.correct_count = stats.correct_count
        self.state.error_count = stats.error_count
        self.state.is_complete = typed_text == self.target_text
        self.state.is_time_up = self._is_time_up()
        return self.state

    def tick(self) -> SessionState:
        self._update_time()
        if not self.state.is_complete and self._is_time_up():
            self.state.is_time_up = True
        return self.state

    def pause(self) -> None:
        if self._started_at is None or self._paused_started_at is not None or not self.state.is_running:
            return
        self._update_time()
        self._paused_started_at = monotonic()
        self.state.is_running = False

    def resume(self) -> None:
        self.begin_timing()

    def finalize(self) -> SessionResult:
        self._update_time()
        duration_sec = self.state.elapsed_ms / 1000.0
        return compute_result(
            correct_chars=self.state.correct_count,
            error_chars=self.state.error_count,
            duration_sec=duration_sec,
        )

    def _update_time(self) -> None:
        if self._started_at is None:
            return
        now = monotonic()
        paused_total_ms = self._paused_total_ms
        if self._paused_started_at is not None:
            paused_total_ms += int((now - self._paused_started_at) * 1000)
        raw_elapsed_ms = int((now - self._started_at) * 1000)
        self.state.elapsed_ms = max(0, raw_elapsed_ms - paused_total_ms)

    def _is_time_up(self) -> bool:
        if self.config.timer_seconds is None:
            return False
        return self.state.elapsed_ms >= self.config.timer_seconds * 1000
