from __future__ import annotations

import time
import unittest

from typing_app.core import TypingSession, calculate_typing_stats, compute_result
from typing_app.models import SessionConfig


class TypingEngineTests(unittest.TestCase):
    def test_stats_count_mismatches_and_extras(self) -> None:
        stats = calculate_typing_stats("abc", "abxd")
        self.assertEqual(stats.correct_count, 2)
        self.assertEqual(stats.error_count, 2)

    def test_backspace_recomputes_errors(self) -> None:
        session = TypingSession("abcd", SessionConfig(timer_seconds=None))
        session.start()
        session.begin_timing()
        session.update_typed_text("abcx")
        self.assertEqual(session.state.error_count, 1)
        session.update_typed_text("abc")
        self.assertEqual(session.state.error_count, 0)

    def test_timer_expiry_ends_session(self) -> None:
        session = TypingSession("abcd", SessionConfig(timer_seconds=1))
        session.start()
        session.begin_timing()
        time.sleep(1.05)
        state = session.tick()
        self.assertTrue(state.is_time_up)

    def test_pause_freezes_elapsed_until_resume(self) -> None:
        session = TypingSession("abcd", SessionConfig(timer_seconds=2))
        session.start()
        session.begin_timing()
        time.sleep(0.35)
        session.tick()
        elapsed_before_pause = session.state.elapsed_ms

        session.pause()
        time.sleep(0.5)
        session.tick()
        elapsed_during_pause = session.state.elapsed_ms
        self.assertLess(abs(elapsed_during_pause - elapsed_before_pause), 120)
        self.assertFalse(session.state.is_time_up)

        session.resume()
        time.sleep(0.35)
        session.tick()
        elapsed_after_resume = session.state.elapsed_ms
        self.assertGreater(elapsed_after_resume, elapsed_during_pause + 200)

    def test_timer_stays_idle_until_typing_begins(self) -> None:
        session = TypingSession("abcd", SessionConfig(timer_seconds=1))
        session.start()
        time.sleep(0.2)
        session.tick()
        self.assertEqual(session.state.elapsed_ms, 0)
        self.assertFalse(session.state.is_running)

        session.begin_timing()
        time.sleep(0.2)
        session.tick()
        self.assertGreater(session.state.elapsed_ms, 100)
        self.assertTrue(session.state.is_running)

    def test_compute_result_formula(self) -> None:
        result = compute_result(correct_chars=250, error_chars=25, duration_sec=60)
        self.assertEqual(result.gross_wpm, 55.0)
        self.assertEqual(result.net_wpm, 45.0)
        self.assertAlmostEqual(result.accuracy_pct, 90.91, places=2)


if __name__ == "__main__":
    unittest.main()
