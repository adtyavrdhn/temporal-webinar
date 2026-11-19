"""The Hacker News API: fetch posts and turn their HTML into plain text."""

import asyncio
import html
import re

import httpx2

from hiring.posts import POSTS

ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"
_client = httpx2.AsyncClient(timeout=10)


async def get_thread(thread_id: int) -> list[int]:
    """The ids of the posts in a Hacker News thread, oldest first."""
    item = (await _client.get(ITEM.format(thread_id))).raise_for_status().json()
    kids = sorted(item.get("kids", []))  # kids: the thread's top-level comments, which are the job posts
    texts = await get_posts(kids)
    return [i for i in kids if texts[i]]  # skip posts deleted on HN


async def get_post(post_id: int) -> str:
    """The text of one "Who is hiring?" post, by its id."""
    item: dict[str, str] = (await _client.get(ITEM.format(post_id))).raise_for_status().json() or {}
    if item.get("dead") or not item.get("text"):
        # Deleted or flagged on HN. For 2 of the 158 we labelled by hand, use the text we labelled.
        return POSTS.get(post_id, "")
    text = re.sub(r"<p>", "\n\n", item["text"])
    text = re.sub(r"<br\s*/?>", "\n", text)
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


async def get_posts(post_ids: list[int]) -> dict[int, str]:
    """The text of each post, by its id."""
    # HN serves one item per request, so fetch them all at once.
    return dict(zip(post_ids, await asyncio.gather(*(get_post(i) for i in post_ids))))
