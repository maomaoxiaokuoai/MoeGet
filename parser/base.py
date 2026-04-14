from pathlib import Path
import sys

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from core.base import BaseParser, ImgInfo, VideoAuthor, VideoInfo, VideoSource

__all__ = ["BaseParser", "ImgInfo", "VideoAuthor", "VideoInfo", "VideoSource"]
