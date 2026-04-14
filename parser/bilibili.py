from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

import httpx

from core.base import BaseParser, VideoAuthor, VideoInfo
from utils.bili_cookie import build_cookie_header, load_bili_cookies


class BiliBili(BaseParser):
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    )
    DASH_QUALITY_CANDIDATES = (120, 116, 112, 80, 64)

    def get_default_headers(self, use_cookie: bool = True) -> dict:
        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": "https://www.bilibili.com/",
        }
        if use_cookie:
            cookie_header = build_cookie_header(load_bili_cookies())
            if cookie_header:
                headers["Cookie"] = cookie_header
        return headers

    def has_cookie(self) -> bool:
        return bool(build_cookie_header(load_bili_cookies()))

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        bvid = await self._get_bvid_from_url(share_url)
        return await self.parse_video_id(bvid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        view_resp = await self._request_json(
            f"https://api.bilibili.com/x/web-interface/view?bvid={video_id}",
            use_cookie=self.has_cookie(),
        )
        if view_resp.get("code") != 0 or not view_resp.get("data", {}).get("pages"):
            raise ValueError(f"无法获取视频信息: {view_resp.get('message', '未知错误')}")

        data = view_resp["data"]
        first_page_cid = data["pages"][0]["cid"]

        if self.has_cookie():
            try:
                return await self._build_dash_video_info(video_id, first_page_cid, data)
            except Exception:
                pass

        return await self._build_html5_video_info(video_id, first_page_cid, data)

    async def _build_dash_video_info(self, video_id: str, cid: int, view_data: dict) -> VideoInfo:
        play_data = await self._request_best_dash_play_data(video_id, cid)
        dash_data = play_data.get("dash") or {}
        selected_video = self._select_best_video_stream(dash_data.get("video") or [])
        selected_audio = self._select_best_audio_stream(dash_data.get("audio") or [])

        video_url = selected_video.get("baseUrl") or selected_video.get("base_url") or ""
        audio_url = selected_audio.get("baseUrl") or selected_audio.get("base_url") or ""
        if not video_url or not audio_url:
            raise ValueError("高画质流信息不完整")

        return self._build_video_info(
            view_data=view_data,
            video_url=video_url,
            audio_url=audio_url,
            quality_label=self._build_quality_label(selected_video, play_data),
            requires_mux=True,
        )

    async def _request_best_dash_play_data(self, video_id: str, cid: int) -> dict:
        errors: list[str] = []
        for quality in self.DASH_QUALITY_CANDIDATES:
            play_resp = await self._request_json(
                "https://api.bilibili.com/x/player/playurl?"
                f"bvid={video_id}&cid={cid}&qn={quality}&fnval=16&fnver=0&fourk=1",
                use_cookie=True,
            )
            if play_resp.get("code") != 0:
                errors.append(
                    f"qn={quality}: {play_resp.get('message', '未知错误')} (code: {play_resp.get('code')})"
                )
                continue

            play_data = play_resp.get("data", {})
            dash_data = play_data.get("dash") or {}
            video_streams = dash_data.get("video") or []
            audio_streams = dash_data.get("audio") or []
            if video_streams and audio_streams:
                return play_data

            errors.append(f"qn={quality}: dash 资源不完整")

        raise ValueError("; ".join(errors) or "高画质 DASH 资源请求失败")

    async def _build_html5_video_info(self, video_id: str, cid: int, view_data: dict) -> VideoInfo:
        play_resp = await self._request_json(
            "https://api.bilibili.com/x/player/playurl?"
            f"otype=json&fnver=0&fnval=0&qn=64&bvid={video_id}&cid={cid}&platform=html5",
            use_cookie=False,
        )
        if play_resp.get("code") != 0:
            raise ValueError(
                f"B站 API 返回错误: {play_resp.get('message', '未知错误')} "
                f"(code: {play_resp.get('code')})"
            )

        play_data = play_resp.get("data", {})
        durl_list = play_data.get("durl") or []
        video_url = durl_list[0].get("url", "") if durl_list else ""
        if not video_url:
            raise ValueError("无法获取视频播放链接")

        return self._build_video_info(
            view_data=view_data,
            video_url=video_url,
            audio_url="",
            quality_label="720P",
            requires_mux=False,
        )

    def _build_video_info(
        self,
        view_data: dict,
        video_url: str,
        audio_url: str,
        quality_label: str,
        requires_mux: bool,
    ) -> VideoInfo:
        video_info = VideoInfo(
            title=view_data.get("title", ""),
            video_url=video_url,
            cover_url=view_data.get("pic", ""),
            music_url=audio_url,
            images=[],
        )

        owner = view_data.get("owner", {})
        video_info.author = VideoAuthor(
            uid=str(owner.get("mid", "")),
            name=owner.get("name", ""),
            avatar=owner.get("face", ""),
        )
        video_info.source = "bilibili"
        video_info.requires_mux = requires_mux
        video_info.video_quality_label = quality_label
        return video_info

    def _select_best_video_stream(self, video_streams: list[dict]) -> dict:
        if not video_streams:
            return {}

        def stream_score(stream: dict) -> tuple[int, int, int]:
            codecs = str(stream.get("codecs", "")).lower()
            prefer_avc = 1 if codecs.startswith("avc") else 0
            return (
                int(stream.get("id") or 0),
                int(stream.get("height") or 0),
                prefer_avc,
            )

        return max(video_streams, key=stream_score)

    def _select_best_audio_stream(self, audio_streams: list[dict]) -> dict:
        if not audio_streams:
            return {}
        return max(audio_streams, key=lambda stream: int(stream.get("bandwidth") or 0))

    def _build_quality_label(self, video_stream: dict, play_data: dict) -> str:
        height = int(video_stream.get("height") or 0)
        if height >= 2160:
            return "4K"
        if height >= 1440:
            return "2K"
        if height >= 1080:
            return "1080P"
        if height >= 720:
            return "720P"
        if height > 0:
            return f"{height}P"

        quality_id = int(play_data.get("quality") or 0)
        quality_labels = {
            120: "4K",
            116: "1080P60",
            112: "1080P+",
            80: "1080P",
            64: "720P",
            32: "480P",
            16: "360P",
        }
        return quality_labels.get(quality_id, "视频")

    async def _get_bvid_from_url(self, raw_url: str) -> str:
        try:
            parsed_url = urlparse(raw_url)
        except Exception as err:
            raise ValueError("URL 格式无效") from err

        if "b23.tv" in parsed_url.netloc:
            async with httpx.AsyncClient(follow_redirects=False) as client:
                resp = await client.get(raw_url, headers=self.get_default_headers(use_cookie=False))
                location = resp.headers.get("location")
                if not location:
                    raise ValueError("无法从 b23.tv 获取重定向链接")
                return await self._get_bvid_from_url(location)

        if "bilibili.com" in parsed_url.netloc:
            path = parsed_url.path.strip("/")
            parts = path.split("/")
            if len(parts) >= 2 and parts[0] == "video" and parts[1].startswith("BV"):
                return parts[1]

        raise ValueError("不是有效的 B站视频链接")

    async def _request_json(self, api_url: str, use_cookie: bool) -> dict:
        headers = self.get_default_headers(use_cookie=use_cookie)
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
        if response.status_code != 200:
            raise ValueError(f"HTTP 请求失败，状态码: {response.status_code}")
        return json.loads(response.text)
