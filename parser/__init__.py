from __future__ import annotations

from importlib import import_module
from urllib.parse import urlparse

from core.base import BaseParser, VideoInfo, VideoSource

VIDEO_SOURCE_INFO_MAPPING: dict[VideoSource, dict[str, str | list[str]]] = {
    VideoSource.AcFun: {
        "domain_list": ["www.acfun.cn"],
        "module_path": "parser.acfun",
        "class_name": "AcFun",
    },
    VideoSource.DouPai: {
        "domain_list": ["doupai.cc"],
        "module_path": "parser.doupai",
        "class_name": "DouPai",
    },
    VideoSource.DouYin: {
        "domain_list": ["v.douyin.com", "www.iesdouyin.com", "www.douyin.com"],
        "module_path": "parser.douyin",
        "class_name": "DouYin",
    },
    VideoSource.HaoKan: {
        "domain_list": ["haokan.baidu.com", "haokan.hao123.com"],
        "module_path": "parser.haokan",
        "class_name": "HaoKan",
    },
    VideoSource.BiliBili: {
        "domain_list": ["www.bilibili.com", "b23.tv", "m.bilibili.com"],
        "module_path": "parser.bilibili",
        "class_name": "BiliBili",
    },
    VideoSource.HuYa: {
        "domain_list": ["v.huya.com"],
        "module_path": "parser.huya",
        "class_name": "HuYa",
    },
    VideoSource.KuaiShou: {
        "domain_list": ["v.kuaishou.com"],
        "module_path": "parser.kuaishou",
        "class_name": "KuaiShou",
    },
    VideoSource.LiShiPin: {
        "domain_list": ["www.pearvideo.com"],
        "module_path": "parser.lishipin",
        "class_name": "LiShiPin",
    },
    VideoSource.LvZhou: {
        "domain_list": ["weibo.cn"],
        "module_path": "parser.lvzhou",
        "class_name": "LvZhou",
    },
    VideoSource.MeiPai: {
        "domain_list": ["meipai.com"],
        "module_path": "parser.meipai",
        "class_name": "MeiPai",
    },
    VideoSource.PiPiGaoXiao: {
        "domain_list": ["h5.pipigx.com"],
        "module_path": "parser.pipigaoxiao",
        "class_name": "PiPiGaoXiao",
    },
    VideoSource.PiPiXia: {
        "domain_list": ["h5.pipix.com"],
        "module_path": "parser.pipixia",
        "class_name": "PiPiXia",
    },
    VideoSource.QuanMin: {
        "domain_list": ["xspshare.baidu.com"],
        "module_path": "parser.quanmin",
        "class_name": "QuanMin",
    },
    VideoSource.QuanMinKGe: {
        "domain_list": ["kg.qq.com"],
        "module_path": "parser.quanminkge",
        "class_name": "QuanMinKGe",
    },
    VideoSource.SixRoom: {
        "domain_list": ["6.cn"],
        "module_path": "parser.sixroom",
        "class_name": "SixRoom",
    },
    VideoSource.WeiBo: {
        "domain_list": ["weibo.com"],
        "module_path": "parser.weibo",
        "class_name": "WeiBo",
    },
    VideoSource.WeiShi: {
        "domain_list": ["isee.weishi.qq.com"],
        "module_path": "parser.weishi",
        "class_name": "WeiShi",
    },
    VideoSource.XiGua: {
        "domain_list": ["v.ixigua.com", "www.ixigua.com"],
        "module_path": "parser.xigua",
        "class_name": "XiGua",
    },
    VideoSource.XinPianChang: {
        "domain_list": ["xinpianchang.com"],
        "module_path": "parser.xinpianchang",
        "class_name": "XinPianChang",
    },
    VideoSource.ZuiYou: {
        "domain_list": ["share.xiaochuankeji.cn"],
        "module_path": "parser.zuiyou",
        "class_name": "ZuiYou",
    },
    VideoSource.RedBook: {
        "domain_list": ["www.xiaohongshu.com", "xhslink.com"],
        "module_path": "parser.redbook",
        "class_name": "RedBook",
    },
    VideoSource.Twitter: {
        "domain_list": ["twitter.com", "x.com", "t.co", "mobile.twitter.com"],
        "module_path": "parser.twitter",
        "class_name": "Twitter",
    },
}

_PARSER_CLASS_CACHE: dict[VideoSource, type[BaseParser]] = {}


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")


def resolve_source(share_url: str) -> VideoSource:
    host = urlparse(share_url).netloc.lower()
    if not host:
        raise ValueError(f"share url [{share_url}] does not have source config")

    for item_source, item_source_info in VIDEO_SOURCE_INFO_MAPPING.items():
        domain_list = item_source_info["domain_list"]
        if any(_host_matches(host, domain) for domain in domain_list):
            return item_source

    raise ValueError(f"share url [{share_url}] does not have source config")


def get_parser_class(source: VideoSource) -> type[BaseParser]:
    if source in _PARSER_CLASS_CACHE:
        return _PARSER_CLASS_CACHE[source]

    source_info = VIDEO_SOURCE_INFO_MAPPING[source]
    module = import_module(str(source_info["module_path"]))
    parser_class = getattr(module, str(source_info["class_name"]))
    if not issubclass(parser_class, BaseParser):
        raise TypeError(f"{parser_class.__name__} must inherit BaseParser")

    _PARSER_CLASS_CACHE[source] = parser_class
    return parser_class


async def parse_video_share_url(share_url: str) -> VideoInfo:
    parser_class = get_parser_class(resolve_source(share_url))
    return await parser_class().parse_share_url(share_url)


async def parse_video_id(source: VideoSource, video_id: str) -> VideoInfo:
    if not video_id or not source:
        raise ValueError("video_id or source is empty")

    parser_class = get_parser_class(source)
    return await parser_class().parse_video_id(video_id)


__all__ = [
    "VIDEO_SOURCE_INFO_MAPPING",
    "VideoInfo",
    "VideoSource",
    "get_parser_class",
    "parse_video_id",
    "parse_video_share_url",
    "resolve_source",
]
