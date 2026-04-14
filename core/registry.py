from __future__ import annotations

__all__ = [
    "VIDEO_SOURCE_INFO_MAPPING",
    "get_parser_class",
    "parse_video_id",
    "parse_video_share_url",
    "resolve_source",
]


def __getattr__(name: str):
    if name in set(__all__):
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
