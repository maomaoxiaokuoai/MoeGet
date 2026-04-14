from pathlib import Path
import sys

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

import httpx

from utils import get_val_from_url_by_query_key

from core.base import BaseParser, VideoAuthor, VideoInfo


class ZuiYou(BaseParser):
    """
    最右
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = get_val_from_url_by_query_key(share_url, "pid")
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        int_video_id = int(video_id)
        req_url = "https://share.xiaochuankeji.cn/planck/share/post/detail_h5"
        post_data = {
            "h_av": "5.2.13.011",
            "pid": int_video_id,
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                req_url, headers=self.get_default_headers(), json=post_data
            )
            response.raise_for_status()

        json_data = response.json()
        data = json_data["data"]["post"]
        video_key = str(data["imgs"][0]["id"])

        video_info = VideoInfo(
            video_url=data["videos"][video_key]["url"],
            cover_url="",
            title=data["content"],
            author=VideoAuthor(
                uid=str(data["member"]["id"]),
                name=data["member"]["name"],
                avatar=data["member"]["avatar_urls"]["origin"]["urls"][0],
            ),
        )
        return video_info
