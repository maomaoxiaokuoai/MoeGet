from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from enum import Enum
from functools import lru_cache
from typing import Dict, List

FALLBACK_IOS_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 "
    "Mobile/15E148 Safari/604.1"
)


class VideoSource(Enum):
    DouYin = "douyin"
    KuaiShou = "kuaishou"
    PiPiXia = "pipixia"
    WeiBo = "weibo"
    WeiShi = "weishi"
    LvZhou = "lvzhou"
    ZuiYou = "zuiyou"
    QuanMin = "quanmin"
    XiGua = "xigua"
    LiShiPin = "lishipin"
    PiPiGaoXiao = "pipigaoxiao"
    HuYa = "huya"
    AcFun = "acfun"
    DouPai = "doupai"
    MeiPai = "meipai"
    QuanMinKGe = "quanminkge"
    SixRoom = "sixroom"
    XinPianChang = "xinpianchang"
    HaoKan = "haokan"
    BiliBili = "bilibili"
    RedBook = "redbook"
    Twitter = "twitter"


@dataclasses.dataclass
class VideoAuthor:
    uid: str = ""
    name: str = ""
    avatar: str = ""


@dataclasses.dataclass
class ImgInfo:
    url: str = ""
    live_photo_url: str = ""


@dataclasses.dataclass
class VideoInfo:
    video_url: str
    cover_url: str
    title: str = ""
    music_url: str = ""
    images: List[ImgInfo] = dataclasses.field(default_factory=list)
    author: VideoAuthor = dataclasses.field(default_factory=VideoAuthor)


@lru_cache(maxsize=1)
def get_default_user_agent() -> str:
    try:
        import fake_useragent

        return fake_useragent.UserAgent(os=["ios"]).random
    except Exception:
        return FALLBACK_IOS_USER_AGENT


class BaseParser(ABC):
    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        return {
            "User-Agent": get_default_user_agent(),
        }

    @abstractmethod
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        raise NotImplementedError

    @abstractmethod
    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError
