from __future__ import annotations

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo, VideoSource

__all__ = [
    "BaseParser",
    "ImgInfo",
    "VideoAuthor",
    "VideoInfo",
    "VideoSource",
    "VIDEO_SOURCE_INFO_MAPPING",
    "get_parser_class",
    "parse_video_id",
    "parse_video_share_url",
    "resolve_source",
]


def __getattr__(name: str):
    if name in {
        "VIDEO_SOURCE_INFO_MAPPING",
        "get_parser_class",
        "parse_video_id",
        "parse_video_share_url",
        "resolve_source",
    }:
        from parser import (
            VIDEO_SOURCE_INFO_MAPPING,
            get_parser_class,
            parse_video_id,
            parse_video_share_url,
            resolve_source,
        )

        exports = {
            "VIDEO_SOURCE_INFO_MAPPING": VIDEO_SOURCE_INFO_MAPPING,
            "get_parser_class": get_parser_class,
            "parse_video_id": parse_video_id,
            "parse_video_share_url": parse_video_share_url,
            "resolve_source": resolve_source,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
