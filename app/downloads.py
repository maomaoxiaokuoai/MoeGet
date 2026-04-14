from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

from utils.bili_cookie import build_cookie_header

from .state import AppState

URL_REG = re.compile(r"https?://[^\s]+")
TRAILING_URL_PUNCTUATION = "。，！？；：,.!?:;\"'”’）)]】〉》>"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DEFAULT_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}
FALLBACK_EXTENSIONS = {
    "cover": ".jpg",
    "video": ".mp4",
    "audio": ".mp3",
    "image": ".jpg",
    "livephoto": ".mp4",
}


def sanitize_filename(value: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("_", value).strip().rstrip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "untitled"


def extract_share_url(text: str) -> str | None:
    matched_url = URL_REG.search(text or "")
    if matched_url is None:
        return None

    share_url = matched_url.group().strip().rstrip(TRAILING_URL_PUNCTUATION)
    return share_url or None


def normalize_download_url(request_url: str) -> str:
    if request_url.startswith("//"):
        request_url = f"https:{request_url}"

    parsed = urlparse(request_url)
    host = parsed.netloc.lower()
    if parsed.scheme == "http" and (
        host.endswith(".hdslb.com")
        or host == "hdslb.com"
        or host.endswith(".bilibili.com")
        or host.endswith(".bilivideo.com")
        or host == "bilivideo.com"
    ):
        request_url = request_url.replace("http://", "https://", 1)

    return request_url


def build_download_headers(request_url: str) -> dict[str, str]:
    headers = dict(DEFAULT_DOWNLOAD_HEADERS)
    host = urlparse(request_url).netloc.lower()

    referer_rules = [
        (
            (".hdslb.com", "hdslb.com", ".bilibili.com", "bilibili.com", ".bilivideo.com", "bilivideo.com"),
            "https://www.bilibili.com/",
        ),
        ((".douyin.com", "douyin.com", ".iesdouyin.com", "iesdouyin.com"), "https://www.douyin.com/"),
        ((".xiaohongshu.com", "xiaohongshu.com", ".xhslink.com", "xhslink.com"), "https://www.xiaohongshu.com/"),
        ((".kuaishou.com", "kuaishou.com"), "https://www.kuaishou.com/"),
        ((".weibo.com", "weibo.com", ".sinaimg.cn", "sinaimg.cn"), "https://weibo.com/"),
    ]

    for suffixes, referer in referer_rules:
        if any(host == suffix.lstrip(".") or host.endswith(suffix) for suffix in suffixes):
            headers["Referer"] = referer
            break

    if "bilibili" in host or "hdslb.com" in host or "bilivideo.com" in host:
        cookie_header = build_cookie_header(AppState.refresh_bili_cookies())
        if cookie_header:
            headers["Cookie"] = cookie_header
        headers["Origin"] = "https://www.bilibili.com"

    return headers


def get_download_extension(request_url: str, response, fallback: str) -> str:
    filename = ""
    content_disposition = response.headers.get("content-disposition", "")
    filename_match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
    if filename_match:
        filename = unquote(filename_match.group(1))
    else:
        filename_match = re.search(r'filename="?([^";]+)"?', content_disposition)
        if filename_match:
            filename = filename_match.group(1)

    suffix = Path(filename).suffix
    if not suffix:
        suffix = Path(urlparse(str(response.url or request_url)).path).suffix

    if suffix:
        return suffix.lower()

    content_type = response.headers.get("content-type", "").split(";")[0].lower()
    content_type_extensions = {
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    return content_type_extensions.get(content_type, fallback)


def build_download_path(base_dir: Path, title: str, kind: str, index: int | None, extension: str) -> Path:
    safe_title = sanitize_filename(title)
    if AppState.create_title_folder:
        target_dir = base_dir / safe_title
    else:
        target_dir = base_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    kind_labels = {
        "cover": "cover",
        "video": "video",
        "audio": "audio",
        "image": "image",
        "livephoto": "livephoto",
    }
    kind_label = kind_labels.get(kind, "file")
    index_suffix = f"_{index:03d}" if index is not None else ""
    file_name = f"{safe_title}_{kind_label}{index_suffix}{extension}"
    return target_dir / file_name


def build_download_items(video_info: dict) -> list[dict]:
    items: list[dict] = []

    if AppState.download_cover and video_info.get("cover_url"):
        items.append({"url": video_info["cover_url"], "kind": "cover", "index": None})
    if video_info.get("video_url"):
        items.append({"url": video_info["video_url"], "kind": "video", "index": None})
    if video_info.get("music_url"):
        items.append({"url": video_info["music_url"], "kind": "audio", "index": None})

    for index, image in enumerate(video_info.get("images", []), start=1):
        if image.get("url"):
            items.append({"url": image["url"], "kind": "image", "index": index})
        if image.get("live_photo_url"):
            items.append({"url": image["live_photo_url"], "kind": "livephoto", "index": index})

    return items


def get_resource_count(video_info: dict) -> int:
    resource_count = len(build_download_items(video_info))
    if video_info.get("requires_mux") and video_info.get("video_url") and video_info.get("music_url"):
        resource_count -= 1
    return max(resource_count, 0)


def get_preview_url(video_info: dict) -> str:
    if video_info.get("cover_url"):
        return video_info["cover_url"]

    images = video_info.get("images", [])
    if images:
        first_image = images[0]
        return first_image.get("url") or first_image.get("live_photo_url") or ""

    return ""


def get_ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def build_mux_output_path(save_path: Path, title: str) -> Path:
    safe_title = sanitize_filename(title)
    if AppState.create_title_folder:
        target_dir = save_path / safe_title
    else:
        target_dir = save_path
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{safe_title}.mp4"


def mux_media_files(save_path: Path, video_info: dict, saved_files: list[Path]) -> list[Path]:
    if not video_info.get("requires_mux"):
        return saved_files

    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path is None:
        return saved_files

    video_file = next((path for path in saved_files if "_video" in path.stem), None)
    audio_file = next((path for path in saved_files if "_audio" in path.stem), None)
    if video_file is None or audio_file is None:
        return saved_files

    output_path = build_mux_output_path(save_path, video_info.get("title") or "untitled")
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_file),
        "-i",
        str(audio_file),
        "-c",
        "copy",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True)
    if completed.returncode != 0:
        stderr_text = completed.stderr.decode("utf-8", errors="replace").strip() if completed.stderr else ""
        stdout_text = completed.stdout.decode("utf-8", errors="replace").strip() if completed.stdout else ""
        error_message = stderr_text or stdout_text or "ffmpeg 合并失败"
        raise ValueError(error_message)

    try:
        video_file.unlink(missing_ok=True)
        audio_file.unlink(missing_ok=True)
    except OSError:
        pass

    merged_files = [path for path in saved_files if path not in {video_file, audio_file}]
    merged_files.append(output_path)
    return merged_files


async def download_assets(save_path: Path, video_info: dict, progress_callback=None) -> list[Path]:
    import httpx

    items = build_download_items(video_info)
    if not items:
        raise ValueError("没有可保存的资源")

    save_path.mkdir(parents=True, exist_ok=True)
    title = video_info.get("title") or "untitled"
    saved_files: list[Path] = []
    total_items = len(items)

    if progress_callback is not None:
        progress_callback(0, f"准备保存 0/{total_items}")

    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
        total_bytes = 0
        all_sizes_known = True

        for item in items:
            normalized_url = normalize_download_url(item["url"])
            request_headers = build_download_headers(normalized_url)
            async with client.stream("GET", normalized_url, headers=request_headers) as response:
                response.raise_for_status()
                item["normalized_url"] = normalized_url
                item["headers"] = request_headers
                item["size"] = int(response.headers.get("content-length") or 0)
                if item["size"] <= 0:
                    all_sizes_known = False
                total_bytes += max(item["size"], 0)

        downloaded_total_bytes = 0

        for item_index, item in enumerate(items, start=1):
            normalized_url = item["normalized_url"]
            request_headers = item["headers"]
            async with client.stream("GET", normalized_url, headers=request_headers) as response:
                response.raise_for_status()
                extension = get_download_extension(
                    normalized_url,
                    response,
                    FALLBACK_EXTENSIONS.get(item["kind"], ".bin"),
                )
                file_path = build_download_path(save_path, title, item["kind"], item["index"], extension)
                downloaded_bytes = 0

                if progress_callback is not None:
                    if all_sizes_known and total_bytes > 0:
                        progress_callback(
                            int((downloaded_total_bytes / total_bytes) * 100),
                            f"正在保存 {item_index}/{total_items}",
                        )
                    else:
                        progress_callback(
                            int(((item_index - 1) / total_items) * 100),
                            f"正在保存 {item_index}/{total_items}",
                        )

                with file_path.open("wb") as file_obj:
                    async for chunk in response.aiter_bytes():
                        file_obj.write(chunk)
                        if not chunk:
                            continue
                        downloaded_bytes += len(chunk)
                        if progress_callback is not None:
                            if all_sizes_known and total_bytes > 0:
                                current_total = downloaded_total_bytes + downloaded_bytes
                                progress_callback(
                                    int((current_total / total_bytes) * 100),
                                    f"正在保存 {item_index}/{total_items}",
                                )
                            else:
                                item_size = int(item.get("size") or 0)
                                if item_size > 0:
                                    item_ratio = min(downloaded_bytes / item_size, 1.0)
                                    progress_callback(
                                        int((((item_index - 1) + item_ratio) / total_items) * 100),
                                        f"正在保存 {item_index}/{total_items}",
                                    )
                saved_files.append(file_path)
                downloaded_total_bytes += downloaded_bytes
                if progress_callback is not None:
                    if all_sizes_known and total_bytes > 0:
                        progress_callback(
                            int((downloaded_total_bytes / total_bytes) * 100),
                            f"已完成 {item_index}/{total_items}",
                        )
                    else:
                        progress_callback(
                            int((item_index / total_items) * 100),
                            f"已完成 {item_index}/{total_items}",
                        )

    if progress_callback is not None:
        if video_info.get("requires_mux") and get_ffmpeg_path():
            progress_callback(100, "正在封装音视频...")
        else:
            progress_callback(100, f"已完成 {total_items}/{total_items}")

    return mux_media_files(save_path, video_info, saved_files)
