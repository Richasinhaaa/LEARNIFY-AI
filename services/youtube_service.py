# ══════════════════════════════════════════════════════════════════════════════
# services/youtube_service.py — YouTube Search
#
# Single responsibility: search YouTube and return normalised video dicts.
#
# Design decisions:
#   - Graceful degradation: if youtubesearchpython is not installed,
#     or the search fails, returns an empty list (never raises)
#   - Returns a consistent schema regardless of search backend
#   - Fallback placeholder generation is CLEARLY labelled so the UI
#     can warn users rather than silently showing fake data
# ══════════════════════════════════════════════════════════════════════════════

from typing import List, Dict, Optional

try:
    from youtubesearchpython import VideosSearch
    YT_AVAILABLE = True
except ImportError:
    YT_AVAILABLE = False

# Gradient palette for video card thumbnails when no real thumbnail exists
_CARD_COLORS = [
    "linear-gradient(135deg,#1e3a8a,#3b82f6)",
    "linear-gradient(135deg,#7c3aed,#a855f7)",
    "linear-gradient(135deg,#059669,#10b981)",
    "linear-gradient(135deg,#b45309,#f59e0b)",
    "linear-gradient(135deg,#dc2626,#f87171)",
]

# Level-specific search query modifiers improve result quality
_LEVEL_SUFFIX = {
    "Beginner":     "for beginners explained simply",
    "Intermediate": "intermediate tutorial explained",
    "Advanced":     "advanced deep dive complete",
}


def search_videos(topic: str, level: str, limit: int = 10) -> List[Dict]:
    """
    Search YouTube for videos matching the topic and level.

    Returns a list of normalised video dicts with keys:
        title, channel, url, vid_id, thumb, desc, duration, views, color
        is_placeholder (bool) — True when real search was unavailable

    Never raises — returns empty list on any failure.
    """
    suffix = _LEVEL_SUFFIX.get(level, "tutorial")
    query = f"{topic} {suffix}"

    if YT_AVAILABLE:
        try:
            results = VideosSearch(query, limit=limit).result().get("result", [])
            return [_normalise(item, idx) for idx, item in enumerate(results)]
        except Exception:
            pass  # Fall through to placeholder

    # Real search unavailable — return empty so caller decides what to show
    return []


def _normalise(item: Dict, idx: int) -> Dict:
    """Convert a raw youtubesearchpython result into our standard schema."""
    desc = " ".join(s.get("text", "") for s in item.get("descriptionSnippet", []))
    link = item.get("link", "#")
    vid_id = link.split("watch?v=")[-1].split("&")[0] if "watch?v=" in link else ""
    thumb = item["thumbnails"][0]["url"] if item.get("thumbnails") else ""
    views_raw = item.get("viewCount", {})
    views = views_raw.get("short", "N/A") if isinstance(views_raw, dict) else "N/A"

    return {
        "title":          item.get("title", ""),
        "channel":        item.get("channel", {}).get("name", ""),
        "url":            link,
        "vid_id":         vid_id,
        "thumb":          thumb,
        "desc":           desc[:300],
        "duration":       item.get("duration", "N/A"),
        "views":          views,
        "color":          _CARD_COLORS[idx % len(_CARD_COLORS)],
        "is_placeholder": False,
    }


def build_placeholders(topic: str, level: str) -> List[Dict]:
    """
    Return clearly-labelled placeholder video dicts when real search fails.
    UI MUST show a warning alongside these — they are not real results.
    """
    channel_names = [
        "freeCodeCamp.org", "Traversy Media", "Tech With Tim",
        "The Net Ninja", "CS Dojo",
    ]
    titles = [
        f"Complete {topic} Course — {level}",
        f"{topic} Full Tutorial {_LEVEL_SUFFIX.get(level, '')}",
        f"Learn {topic} from Scratch",
        f"{topic} Explained — {level} Guide",
        f"Master {topic} — Crash Course",
    ]
    return [
        {
            "title":          titles[i],
            "channel":        channel_names[i],
            "url":            f"https://youtube.com/results?search_query={topic.replace(' ', '+')}",
            "vid_id":         "",
            "thumb":          "",
            "desc":           f"{level} tutorial on {topic}",
            "duration":       "N/A",
            "views":          "N/A",
            "color":          _CARD_COLORS[i],
            "is_placeholder": True,   # UI must display a disclaimer
        }
        for i in range(5)
    ]
