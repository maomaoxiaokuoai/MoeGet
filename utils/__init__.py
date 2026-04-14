from urllib.parse import parse_qs, urlparse


def get_val_from_url_by_query_key(url: str, query_key: str) -> str:
    """从 URL 的 query 参数中取出指定键的值。"""
    url_res = urlparse(url)
    url_query = parse_qs(url_res.query, keep_blank_values=True)

    try:
        query_val = url_query[query_key][0]
    except KeyError as err:
        raise KeyError(f"URL 中不存在 query 参数: {query_key}") from err

    if len(query_val) == 0:
        raise ValueError(f"URL 中 query 参数为空: {query_key}")

    return query_val
