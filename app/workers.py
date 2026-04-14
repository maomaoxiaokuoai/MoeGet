from __future__ import annotations

import asyncio
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .downloads import download_assets


def serialize_video_info(video_info) -> dict:
    author = getattr(video_info, "author", None)
    images = getattr(video_info, "images", []) or []
    return {
        "title": getattr(video_info, "title", "") or "",
        "video_url": getattr(video_info, "video_url", "") or "",
        "cover_url": getattr(video_info, "cover_url", "") or "",
        "music_url": getattr(video_info, "music_url", "") or "",
        "source": getattr(video_info, "source", "") or "",
        "requires_mux": bool(getattr(video_info, "requires_mux", False)),
        "video_quality_label": getattr(video_info, "video_quality_label", "") or "",
        "author": {
            "uid": getattr(author, "uid", "") if author else "",
            "name": getattr(author, "name", "") if author else "",
            "avatar": getattr(author, "avatar", "") if author else "",
        },
        "images": [
            {
                "url": getattr(image, "url", "") or "",
                "live_photo_url": getattr(image, "live_photo_url", "") or "",
            }
            for image in images
        ],
    }


class ParseThread(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, share_url: str, parent=None):
        super().__init__(parent)
        self.share_url = share_url

    def run(self):
        try:
            from parser import parse_video_share_url

            video_info = asyncio.run(parse_video_share_url(self.share_url))
            self.result_ready.emit(serialize_video_info(video_info))
        except Exception as err:
            self.error_occurred.emit(str(err) or err.__class__.__name__)


class DownloadThread(QThread):
    finished_ok = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    progress_changed = pyqtSignal(int, str)

    def __init__(self, save_path: Path, video_info: dict, parent=None):
        super().__init__(parent)
        self.save_path = save_path
        self.video_info = video_info

    def run(self):
        try:
            saved_files = asyncio.run(
                download_assets(
                    self.save_path,
                    self.video_info,
                    progress_callback=self.progress_changed.emit,
                )
            )
            self.finished_ok.emit([str(path) for path in saved_files])
        except Exception as err:
            self.error_occurred.emit(str(err) or err.__class__.__name__)
