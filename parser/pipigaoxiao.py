from pathlib import Path
import sys

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from urllib.parse import urlparse

import fake_useragent
import httpx

from core.base import BaseParser, VideoInfo


class PiPiGaoXiao(BaseParser):
    """
    皮皮搞笑
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        url_res = urlparse(share_url)

        video_id = url_res.path.replace("/pp/post/", "")
        if len(video_id) == 0:
            raise ValueError("parse video_id from share url fail")

        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = "https://share.ippzone.com/ppapi/share/fetch_content"
        async with httpx.AsyncClient() as client:
            headers = {
                "Referer": req_url,
                "Content-Type": "text/plain;charset=UTF-8",
                "User-Agent": fake_useragent.UserAgent(os=["windows"]).random,
            }
            # pid需要是数字，这里直接拼接json字符串，不用json.dumps
            post_content = '{"pid":' + video_id + ',"type":"post","mid":null}'
            response = await client.post(req_url, headers=headers, content=post_content)
            response.raise_for_status()

        json_data = response.json()
        # 接口返回错误
        if "msg" in json_data:
            raise Exception(json_data["msg"])

        data = json_data["data"]["post"]
        img_id = data["imgs"][0]["id"]
        video_url = data["videos"][str(img_id)]["url"]
        cover_url = f"https://file.ippzone.com/img/view/id/{img_id}"

        video_info = VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=data["content"],
        )
        return video_info
