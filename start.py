from __future__ import annotations

import subprocess
import sys


def patch_subprocess_run() -> None:
    original_run = subprocess.run

    def patched_run(*args, **kwargs):
        if kwargs.get("text") and "encoding" not in kwargs and "errors" not in kwargs:
            kwargs["encoding"] = "utf-8"
            kwargs["errors"] = "replace"
        return original_run(*args, **kwargs)

    subprocess.run = patched_run


def load_run():
    from app.main import run

    return run


def patch_clipboard_autopaste() -> None:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from app.downloads import extract_share_url
    from app.window import MainWindow

    original_init = MainWindow.__init__
    original_start_parsing = MainWindow.start_parsing
    original_on_parse_thread_finished = MainWindow.on_parse_thread_finished

    def schedule_clipboard_parse(self, share_url: str) -> None:
        if not share_url:
            return
        self._clipboard_pending_url = share_url
        if self.parse_thread is not None and self.parse_thread.isRunning():
            return
        if getattr(self, "_clipboard_autoparse_scheduled", False):
            return
        self._clipboard_autoparse_scheduled = True

        def trigger():
            self._clipboard_autoparse_scheduled = False
            pending_url = getattr(self, "_clipboard_pending_url", "")
            if not pending_url:
                return
            self.url_input.setText(pending_url)
            self._clipboard_pending_url = ""
            original_start_parsing(self)

        QTimer.singleShot(150, trigger)

    def on_clipboard_changed(self) -> None:
        self._clipboard_watch_timer.start(180)

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._last_clipboard_url = ""
        self._clipboard_pending_url = ""
        self._clipboard_autoparse_scheduled = False
        self._clipboard_watch_timer = QTimer(self)
        self._clipboard_watch_timer.setSingleShot(True)
        self._clipboard_watch_timer.timeout.connect(self.check_clipboard)
        QApplication.clipboard().dataChanged.connect(self.on_clipboard_changed)

    def patched_check_clipboard(self):
        text = QApplication.clipboard().text().strip()
        share_url = extract_share_url(text)
        if not share_url:
            return

        current_url = extract_share_url(self.url_input.text().strip()) or ""
        if share_url == self._last_clipboard_url and share_url == current_url:
            return

        self._last_clipboard_url = share_url
        self.url_input.setText(share_url)
        self.parse_btn.setText("✨ 检测到新链接，正在准备解析")
        self.url_input.setStyleSheet(self.url_input.styleSheet() + "border: 2px solid #FFD700;")
        QTimer.singleShot(800, self.apply_theme)
        schedule_clipboard_parse(self, share_url)

    def patched_start_parsing(self):
        raw_text = self.url_input.text().strip()
        share_url = extract_share_url(raw_text)
        if share_url:
            self._clipboard_pending_url = ""
            self._last_clipboard_url = share_url
        return original_start_parsing(self)

    def patched_on_parse_thread_finished(self):
        original_on_parse_thread_finished(self)
        pending_url = getattr(self, "_clipboard_pending_url", "")
        current_url = extract_share_url(self.url_input.text().strip()) or ""
        if pending_url and pending_url != current_url:
            self.url_input.setText(pending_url)
        if pending_url:
            schedule_clipboard_parse(self, pending_url)

    MainWindow.on_clipboard_changed = on_clipboard_changed
    MainWindow.__init__ = patched_init
    MainWindow.check_clipboard = patched_check_clipboard
    MainWindow.start_parsing = patched_start_parsing
    MainWindow.on_parse_thread_finished = patched_on_parse_thread_finished


if __name__ == "__main__":
    patch_subprocess_run()
    patch_clipboard_autopaste()
    run = load_run()
    sys.exit(run())
