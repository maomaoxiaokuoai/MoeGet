from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

import fake_useragent
import httpx

from core.base import BaseParser, ImgInfo, VideoAuthor, VideoInfo
from utils import get_val_from_url_by_query_key


class WeiBo(BaseParser):
    """微博解析器，支持视频和图文。"""

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        if "show?fid=" in share_url:
            video_id = get_val_from_url_by_query_key(share_url, "fid")
            return await self.parse_video_id(video_id)
        if "/tv/show/" in share_url:
            url_info = urlparse(share_url)
            video_id = url_info.path.replace("/tv/show/", "")
            return await self.parse_video_id(video_id)

        url_info = urlparse(share_url)
        path_parts = url_info.path.strip("/").split("/")
        if len(path_parts) >= 2:
            post_id = path_parts[-1]
            return await self.parse_post_url(post_id, share_url)

        raise Exception("unsupported weibo url format")

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://h5.video.weibo.com/api/component?page=/show/{video_id}"
        headers = {
            "Referer": f"https://h5.video.weibo.com/show/{video_id}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
        }
        post_content = 'data={"Component_Play_Playinfo":{"oid":"' + video_id + '"}}'
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(req_url, headers=headers, content=post_content)
            response.raise_for_status()

        json_data = response.json()
        data = json_data["data"]["Component_Play_Playinfo"]

        video_url = data["stream_url"]
        if len(data["urls"]) > 0:
            # `stream_url` 往往较低码率，优先使用第一条高清 mp4 地址。
            _, first_mp4_url = next(iter(data["urls"].items()))
            video_url = f"https:{first_mp4_url}"

        return VideoInfo(
            video_url=video_url,
            cover_url="https:" + data["cover_image"],
            title=data["title"],
            author=VideoAuthor(
                uid=str(data["user"]["id"]),
                name=data["author"],
                avatar="https:" + data["avatar"],
            ),
        )

    async def parse_post_url(self, post_id: str, original_url: str) -> VideoInfo:
        req_url = f"https://m.weibo.cn/statuses/show?id={post_id}"
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
            "Referer": "https://m.weibo.cn/",
            "Content-Type": "application/json;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(req_url, headers=headers)
                response.raise_for_status()

            json_data = response.json()
            if "data" in json_data:
                return await self._parse_mobile_api_data(json_data["data"])
        except Exception:
            pass

        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(original_url, headers=headers)
            response.raise_for_status()

        return await self._parse_html_page(response.text)

    async def _parse_mobile_api_data(self, data: dict) -> VideoInfo:
        title = data.get("text", "")
        author_info = data.get("user", {})
        author_name = author_info.get("screen_name", "")
        author_avatar = author_info.get("avatar_large", "")

        images: list[ImgInfo] = []
        pics_data = data.get("pics", [])
        for pic in pics_data:
            large_pic_url = ""
            for size in ["large", "original", "bmiddle", "url"]:
                if size in pic and pic[size].get("url"):
                    large_pic_url = pic[size]["url"]
                    break

            if large_pic_url:
                images.append(ImgInfo(url=large_pic_url))

        return VideoInfo(
            video_url="",
            cover_url="",
            title=self._clean_text(title),
            images=images,
            author=VideoAuthor(
                name=author_name,
                avatar=author_avatar,
            ),
        )

    async def _parse_html_page(self, html_content: str) -> VideoInfo:
        pattern = r"\$render_data\s*=\s*(.*?)\[0\]"
        match = re.search(pattern, html_content)
        if not match:
            raise Exception("parse weibo html page fail")

        import json

        data = json.loads(match.group(1) + "[0]")
        status_data = data.get("status", {})
        title = status_data.get("text", "")
        author_info = status_data.get("user", {})
        author_name = author_info.get("screen_name", "")
        author_avatar = author_info.get("avatar_large", "")

        images: list[ImgInfo] = []
        pics_data = status_data.get("pics", [])
        for pic in pics_data:
            large_pic_url = ""
            for size in ["large", "original", "bmiddle", "url"]:
                if size in pic and pic[size].get("url"):
                    large_pic_url = pic[size]["url"]
                    break

            if large_pic_url:
                images.append(ImgInfo(url=large_pic_url))

        return VideoInfo(
            video_url="",
            cover_url="",
            title=self._clean_text(title),
            images=images,
            author=VideoAuthor(
                name=author_name,
                avatar=author_avatar,
            ),
        )

    def _clean_text(self, text: str) -> str:
        cleaned = re.sub(r"<[^>]*>", "", text)
        return cleaned.strip()
