from __future__ import annotations

import asyncio
from typing import Optional

import flet as ft

from typing_app.core import TypingSession
from typing_app.models import SessionConfig, SessionResult
from typing_app.passage import load_passages


class TypingApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.passages = load_passages()
        self.passage = self.passages[0]
        self.session: Optional[TypingSession] = None
        self.result: Optional[SessionResult] = None
        self._session_token = 0
        self.font_size = 16
        self.min_font_size = 12
        self.max_font_size = 30
        self.is_window_focused = True

        self.page.on_keyboard_event = self._on_keyboard_event
        self.page.on_window_event = self._on_window_event

        self.timer_enabled = ft.Checkbox(label="Enable timer", value=False)
        self.timer_input = ft.TextField(label="Timer (seconds)", value="60", width=180)
        self.passage_select = ft.Dropdown(
            label="Passage",
            width=220,
            value=self.passage.id,
            options=[ft.dropdown.Option(key=passage.id, text=passage.title) for passage in self.passages],
            on_change=self._on_passage_change,
        )
        self.start_button = ft.ElevatedButton("Start Practice", on_click=self._on_start)

        self.home_passage_text = ft.Text(size=self.font_size - 1)
        self.home_passage_title = ft.Text(size=18)
        self.target_text = ft.Text(selectable=True, size=self.font_size)
        self.live_text = ft.Text(spans=[], size=self.font_size)
        self.typing_input = ft.TextField(
            label="Type here",
            multiline=True,
            min_lines=6,
            max_lines=10,
            text_size=self.font_size,
            on_change=self._on_type,
        )
        self.elapsed_label = ft.Text("Elapsed: 0.0s")
        self.remaining_label = ft.Text("Remaining: --")
        self.focus_label = ft.Text("Active", color=ft.Colors.GREEN_700)
        self.gross_wpm_label = ft.Text("Gross WPM: 0.00")
        self.net_wpm_label = ft.Text("Net WPM: 0.00")
        self.accuracy_label = ft.Text("Accuracy: 100.00%")
        self.errors_label = ft.Text("Errors: 0")
        self.stop_button = ft.ElevatedButton("Stop", on_click=self._on_stop, color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_700)

        self.result_title = ft.Text(size=22, weight=ft.FontWeight.BOLD)
        self.result_body = ft.Text(size=self.font_size)
        self.restart_button = ft.ElevatedButton("Practice Again", on_click=self._go_home)

        self._go_home(None)

    def _go_home(self, _: object | None) -> None:
        self.session = None
        self.result = None
        self._session_token += 1
        self.page.title = "English Typing App"
        self.page.padding = 24
        self.page.window_width = 980
        self.page.window_height = 760
        self.page.window_min_width = 780
        self.page.window_min_height = 620

        self.page.views.clear()
        self.page.views.append(
            ft.View(
                route="/",
                controls=[
                    ft.Text("English Typing Practice", size=30, weight=ft.FontWeight.BOLD),
                    self.passage_select,
                    self.home_passage_title,
                    ft.Container(
                        content=self.home_passage_text,
                        padding=12,
                        border=ft.border.all(1, ft.Colors.GREY_400),
                        border_radius=8,
                        height=260,
                    ),
                    ft.Text("Shortcut: Ctrl + to increase font, Ctrl - to decrease font", size=13, color=ft.Colors.GREY_700),
                    ft.Row([self.timer_enabled, self.timer_input], spacing=16),
                    self.start_button,
                ],
                vertical_alignment=ft.MainAxisAlignment.START,
            )
        )
        self._apply_font_size()
        self.page.update()

    def _on_passage_change(self, event: ft.ControlEvent) -> None:
        selected_id = event.control.value
        selected_passage = next((passage for passage in self.passages if passage.id == selected_id), None)
        if selected_passage is None:
            return

        self.passage = selected_passage
        self._apply_font_size()
        self.page.update()

    def _on_start(self, _: ft.ControlEvent) -> None:
        timer_seconds = None
        if self.timer_enabled.value:
            try:
                raw_value = int(self.timer_input.value or "")
                if raw_value <= 0:
                    raise ValueError
                timer_seconds = raw_value
            except ValueError:
                self.page.snack_bar = ft.SnackBar(ft.Text("Timer must be a positive integer."))
                self.page.snack_bar.open = True
                self.page.update()
                return

        self.session = TypingSession(self.passage.text, SessionConfig(timer_seconds=timer_seconds))
        self.session.start()
        self._session_token += 1

        self.typing_input.value = ""
        self.target_text.value = self.passage.text
        self.live_text.spans = self._build_spans(self.passage.text, "")
        self._update_metrics()

        self.page.views.clear()
        self.page.views.append(
            ft.View(
                route="/practice",
                controls=[
                    ft.Text("Practice", size=28, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=self.target_text,
                        padding=12,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=8,
                    ),
                    ft.Text("Live correctness overlay", size=14, color=ft.Colors.GREY_700),
                    ft.Container(
                        content=self.live_text,
                        padding=12,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=8,
                    ),
                    self.typing_input,
                    ft.Row([self.elapsed_label, self.remaining_label, self.focus_label], spacing=24),
                    ft.Row([self.gross_wpm_label, self.net_wpm_label, self.accuracy_label, self.errors_label], spacing=24),
                    ft.Row([self.stop_button, ft.OutlinedButton("Back", on_click=self._go_home)], spacing=16),
                ],
                vertical_alignment=ft.MainAxisAlignment.START,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        self._apply_font_size()
        self.page.update()
        self.typing_input.focus()
        self.page.run_task(self._timer_loop, self._session_token)

    async def _timer_loop(self, token: int) -> None:
        while self.session is not None and token == self._session_token:
            self.session.tick()
            self._update_metrics()
            if self.session.state.is_complete or self.session.state.is_time_up:
                self._finish_session()
                return
            self.page.update()
            await asyncio.sleep(0.1)

    def _on_type(self, _: ft.ControlEvent) -> None:
        if self.session is None:
            return

        if self.is_window_focused and self.typing_input.value:
            self.session.begin_timing()

        self.session.update_typed_text(self.typing_input.value or "")
        self.live_text.spans = self._build_spans(self.passage.text, self.session.state.typed_text)
        self._update_metrics()

        if self.session.state.is_complete or self.session.state.is_time_up:
            self._finish_session()
        else:
            self.page.update()

    def _update_metrics(self) -> None:
        if self.session is None:
            return

        state = self.session.state
        result = self.session.finalize()

        elapsed_sec = state.elapsed_ms / 1000.0
        self.elapsed_label.value = f"Elapsed: {elapsed_sec:.1f}s"
        if self.session.config.timer_seconds is None:
            self.remaining_label.value = "Remaining: --"
        else:
            remaining = max(0.0, self.session.config.timer_seconds - elapsed_sec)
            self.remaining_label.value = f"Remaining: {remaining:.1f}s"
        if not self.is_window_focused:
            self.focus_label.value = "Paused (window out of focus)"
            self.focus_label.color = ft.Colors.ORANGE_700
        elif state.is_running:
            self.focus_label.value = "Active"
            self.focus_label.color = ft.Colors.GREEN_700
        else:
            self.focus_label.value = "Waiting for typing"
            self.focus_label.color = ft.Colors.BLUE_700

        self.gross_wpm_label.value = f"Gross WPM: {result.gross_wpm:.2f}"
        self.net_wpm_label.value = f"Net WPM: {result.net_wpm:.2f}"
        self.accuracy_label.value = f"Accuracy: {result.accuracy_pct:.2f}%"
        self.errors_label.value = f"Errors: {state.error_count}"

    def _on_stop(self, _: ft.ControlEvent) -> None:
        self._finish_session("Session Stopped")

    def _finish_session(self, title: str | None = None) -> None:
        if self.session is None:
            return

        self.result = self.session.finalize()
        is_complete = self.session.state.is_complete
        is_time_up = self.session.state.is_time_up
        self.session = None
        self._session_token += 1

        if title is None:
            if is_complete:
                title = "Session Complete"
            elif is_time_up:
                title = "Time's Up"
            else:
                title = "Session Stopped"
        self._show_result(title)

    def _show_result(self, title: str) -> None:
        if self.result is None:
            return

        self.result_title.value = title
        self.result_body.value = (
            f"Gross WPM: {self.result.gross_wpm:.2f}\n"
            f"Net WPM: {self.result.net_wpm:.2f}\n"
            f"Accuracy: {self.result.accuracy_pct:.2f}%\n"
            f"Total chars: {self.result.total_chars}\n"
            f"Correct chars: {self.result.correct_chars}\n"
            f"Error chars: {self.result.error_chars}\n"
            f"Duration: {self.result.duration_sec:.2f}s"
        )

        self.page.views.clear()
        self.page.views.append(
            ft.View(
                route="/result",
                controls=[
                    self.result_title,
                    self.result_body,
                    ft.Row([self.restart_button, ft.OutlinedButton("Home", on_click=self._go_home)], spacing=16),
                ],
                vertical_alignment=ft.MainAxisAlignment.START,
            )
        )
        self._apply_font_size()
        self.page.update()

    @staticmethod
    def _build_spans(target_text: str, typed_text: str) -> list[ft.TextSpan]:
        spans: list[ft.TextSpan] = []
        typed_len = len(typed_text)
        target_len = len(target_text)

        for idx, ch in enumerate(target_text):
            if idx >= typed_len:
                spans.append(ft.TextSpan(ch, style=ft.TextStyle(color=ft.Colors.GREY_500)))
            elif typed_text[idx] == ch:
                spans.append(ft.TextSpan(ch, style=ft.TextStyle(color=ft.Colors.GREEN_700)))
            else:
                spans.append(ft.TextSpan(ch, style=ft.TextStyle(color=ft.Colors.RED_700, bgcolor=ft.Colors.RED_50)))

        if typed_len > target_len:
            extra = typed_text[target_len:]
            spans.append(ft.TextSpan(extra, style=ft.TextStyle(color=ft.Colors.RED_900, bgcolor=ft.Colors.RED_100)))

        return spans

    def _on_keyboard_event(self, event: ft.KeyboardEvent) -> None:
        if not event.ctrl:
            return

        key = (event.key or "").lower()
        increase_keys = {"+", "=", "add", "numpad add"}
        decrease_keys = {"-", "_", "subtract", "numpad subtract"}

        if key in increase_keys:
            self._change_font_size(1)
        elif key in decrease_keys:
            self._change_font_size(-1)

    def _on_window_event(self, event: ft.WindowEvent) -> None:
        event_name = (event.data or "").lower()
        if event_name == "blur":
            self.is_window_focused = False
            if self.session is not None:
                self.session.pause()
                self._update_metrics()
                self.page.update()
        elif event_name == "focus":
            self.is_window_focused = True
            if self.session is not None:
                self._update_metrics()
                self.page.update()

    def _change_font_size(self, delta: int) -> None:
        next_size = max(self.min_font_size, min(self.max_font_size, self.font_size + delta))
        if next_size == self.font_size:
            return

        self.font_size = next_size
        self._apply_font_size()
        self.page.update()

    def _apply_font_size(self) -> None:
        self.home_passage_title.value = f"Passage: {self.passage.title}"
        self.home_passage_text.value = self.passage.text
        self.home_passage_text.size = self.font_size - 1
        self.target_text.size = self.font_size
        self.live_text.size = self.font_size
        self.typing_input.text_size = self.font_size
        self.result_body.size = self.font_size


def main(page: ft.Page) -> None:
    TypingApp(page)
