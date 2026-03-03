"""Optional curated metadata layer for ROMs."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Dict, Any, List


SCRAPER_SCREENSCRAPER = "screenscraper"
SCRAPER_THEGAMESDB = "thegamesdb"
SCRAPER_WIKIPEDIA = "wikipedia"
_SCRAPER_LABELS = {
    SCRAPER_SCREENSCRAPER: "ScreenScraper",
    SCRAPER_THEGAMESDB: "TheGamesDB",
    SCRAPER_WIKIPEDIA: "Wikipedia",
}
_USER_AGENT = "R0MM/2 MetadataScraper (+local desktop app)"


class MetadataStore:
    def __init__(self, path: str = ""):
        self.path = path
        self.data: Dict[str, Any] = {}
        if path:
            self.load(path)

    def load(self, path: str):
        self.path = path
        if not path or not os.path.exists(path):
            self.data = {}
            return
        with open(path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def lookup(self, crc32: str = "", game_name: str = "") -> Dict[str, Any]:
        if crc32 and crc32 in self.data.get('by_crc32', {}):
            return self.data['by_crc32'][crc32]
        if game_name and game_name in self.data.get('by_game', {}):
            return self.data['by_game'][game_name]
        return {}


def _scraper_label(source: str) -> str:
    return _SCRAPER_LABELS.get(str(source or "").strip().lower(), "Metadata")


def _http_json(url: str, timeout: float = 5.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=max(1.0, float(timeout or 5.0))) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    if not raw.strip():
        raise RuntimeError("Metadata provider returned an empty response.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Metadata provider returned an invalid response.") from exc


def _extract_nested_text(node: Any, *paths: str) -> str:
    for path in paths:
        current = node
        ok = True
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                ok = False
                break
        if not ok:
            continue
        if isinstance(current, list):
            for item in current:
                text = _extract_nested_text(item, "")
                if text:
                    return text
            continue
        if isinstance(current, (str, int, float)):
            value = str(current).strip()
            if value:
                return value
    if path == "" and isinstance(node, (str, int, float)):
        value = str(node).strip()
        if value:
            return value
    return ""


def _preferred_lang_codes(language: str) -> List[str]:
    safe = str(language or "").strip().lower()
    if safe.startswith("pt"):
        return ["br", "pt", "wor", "us", "en", "jp", "fr"]
    return ["us", "en", "wor", "jp", "fr", "pt", "br"]


def _extract_first_media_url(node: Any) -> str:
    return _extract_nested_text(
        node,
        "boxart",
        "boxart.front",
        "media.url",
        "medias.media.url",
        "medias.media.image",
        "medias.box2d",
        "image",
        "image_url",
        "thumb",
    )


class ScreenScraperClient:
    base_url = "https://api.screenscraper.fr/api2/jeuRecherche.php"

    def __init__(self, username: str, password: str, devid: str = "", devpassword: str = "", softname: str = "R0MM"):
        self.username = str(username or "").strip()
        self.password = str(password or "").strip()
        self.devid = str(devid or "").strip()
        self.devpassword = str(devpassword or "").strip()
        self.softname = str(softname or "R0MM").strip() or "R0MM"

    def search(self, query: str, system: str = "", limit: int = 6, language: str = "en") -> Dict[str, Any]:
        if not self.devid or not self.devpassword:
            return {"error": "ScreenScraper requires application API credentials (devid/devpassword)."}

        search_text = str(query or "").strip()
        if system:
            search_text = f"{search_text} {str(system or '').strip()}".strip()

        params = {
            "output": "json",
            "devid": self.devid,
            "devpassword": self.devpassword,
            "softname": self.softname,
            "recherche": search_text,
        }
        if self.username and self.password:
            params["ssid"] = self.username
            params["sspassword"] = self.password
        payload = _http_json(f"{self.base_url}?{urllib.parse.urlencode(params)}")
        response = payload.get("response", {}) if isinstance(payload, dict) else {}
        games = response.get("jeu", [])
        if isinstance(games, dict):
            games = [games]
        if not isinstance(games, list):
            games = []

        items: List[Dict[str, Any]] = []
        lang_codes = _preferred_lang_codes(language)
        for game in games[: max(1, min(10, int(limit or 6)))]:
            if not isinstance(game, dict):
                continue
            title_paths = [f"noms.nom_{code}" for code in lang_codes] + ["nom", "name"]
            title = _extract_nested_text(
                game,
                *title_paths,
            )
            if not title:
                continue
            synopsis_paths = [f"synopsis.synopsis_{code}" for code in lang_codes] + ["genres.genre"]
            description = _extract_nested_text(
                game,
                *synopsis_paths,
            )
            game_id = _extract_nested_text(game, "id")
            url = ""
            if game_id:
                url = f"https://www.screenscraper.fr/gameinfos.php?gameid={game_id}"
            image_url = _extract_first_media_url(game)
            items.append(
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "image_url": image_url,
                    "source": _scraper_label(SCRAPER_SCREENSCRAPER),
                }
            )
        return {"query": query, "items": items}


class WikipediaFallbackClient:
    search_url = "https://{lang}.wikipedia.org/w/api.php"
    summary_url = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"

    def search(self, query: str, system: str = "", limit: int = 6, language: str = "en") -> Dict[str, Any]:
        lang_code = "pt" if str(language or "").strip().lower().startswith("pt") else "en"
        search_text = str(query or "").strip()
        if system:
            search_text = f"{search_text} {str(system or '').strip()} video game".strip()
        params = {
            "action": "opensearch",
            "search": search_text,
            "limit": max(1, min(5, int(limit or 1))),
            "namespace": 0,
            "format": "json",
        }
        payload = _http_json(self.search_url.format(lang=lang_code) + "?" + urllib.parse.urlencode(params))
        titles = payload[1] if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], list) else []
        urls = payload[3] if isinstance(payload, list) and len(payload) > 3 and isinstance(payload[3], list) else []
        items: List[Dict[str, Any]] = []
        for idx, raw_title in enumerate(titles):
            title = str(raw_title or "").strip()
            if not title:
                continue
            summary = {}
            try:
                summary = _http_json(
                    self.summary_url.format(lang=lang_code, title=urllib.parse.quote(title, safe=""))
                )
            except Exception:
                summary = {}
            item_url = str(urls[idx] if idx < len(urls) else summary.get("content_urls", {}).get("desktop", {}).get("page", "") or "")
            image_url = _extract_nested_text(summary, "thumbnail.source", "originalimage.source")
            description = str(summary.get("extract", "") or "").strip()
            if not description:
                description = str(summary.get("description", "") or "").strip()
            items.append(
                {
                    "title": str(summary.get("title", "") or title),
                    "description": description,
                    "url": item_url,
                    "image_url": image_url,
                    "source": _scraper_label(SCRAPER_WIKIPEDIA),
                }
            )
        return {"query": query, "items": items}


class TheGamesDBClient:
    base_url = "https://api.thegamesdb.net/v1.1/Games/ByGameName"

    def __init__(self, api_key: str):
        self.api_key = str(api_key or "").strip()

    def search(self, query: str, system: str = "", limit: int = 6, language: str = "en") -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "TheGamesDB requires an API key."}

        search_text = str(query or "").strip()
        if system:
            search_text = f"{search_text} {str(system or '').strip()}".strip()

        params = {
            "apikey": self.api_key,
            "name": search_text,
        }
        payload = _http_json(f"{self.base_url}?{urllib.parse.urlencode(params)}")
        games = ((payload or {}).get("data", {}) or {}).get("games", [])
        if not isinstance(games, list):
            games = []

        items: List[Dict[str, Any]] = []
        for game in games[: max(1, min(10, int(limit or 6)))]:
            if not isinstance(game, dict):
                continue
            title = str(game.get("game_title", "") or "").strip()
            if not title:
                continue
            game_id = str(game.get("id", "") or "").strip()
            description = str(game.get("overview", "") or "").strip()
            url = f"https://thegamesdb.net/game.php?id={game_id}" if game_id else ""
            image_url = _extract_first_media_url(game)
            items.append(
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "image_url": image_url,
                    "source": _scraper_label(SCRAPER_THEGAMESDB),
                }
            )
        return {"query": query, "items": items}


def fetch_remote_metadata_hints(
    query: str,
    settings: Dict[str, Any],
    system: str = "",
    limit: int = 6,
    language: str = "en",
) -> Dict[str, Any]:
    safe_settings = settings if isinstance(settings, dict) else {}
    source = str(safe_settings.get("source", SCRAPER_SCREENSCRAPER) or SCRAPER_SCREENSCRAPER).strip().lower()
    try:
        if source == SCRAPER_THEGAMESDB:
            client = TheGamesDBClient(safe_settings.get("thegamesdb_api_key", ""))
        else:
            client = ScreenScraperClient(
                safe_settings.get("screenscraper_user", ""),
                safe_settings.get("screenscraper_password", ""),
                safe_settings.get("screenscraper_devid", ""),
                safe_settings.get("screenscraper_devpassword", ""),
                safe_settings.get("screenscraper_softname", "R0MM"),
            )
        return client.search(query, system=system, limit=limit, language=language)
    except Exception as exc:
        return {"error": str(exc)}
