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


class DouPai(BaseParser):
    """
    逗拍
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = get_val_from_url_by_query_key(share_url, "id")
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://v2.doupai.cc/topic/{video_id}.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(req_url, headers=self.get_default_headers())
            response.raise_for_status()

        json_data = response.json()
        data = json_data["data"]

        video_info = VideoInfo(
            video_url=data["videoUrl"],
            cover_url=data["imageUrl"],
            title=data["name"],
            author=VideoAuthor(
                uid=data["userId"]["id"],
                name=data["userId"]["name"],
                avatar=data["userId"]["avatar"],
            ),
        )
        return video_info
