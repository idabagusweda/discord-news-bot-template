from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import feedparser
import requests
from bs4 import BeautifulSoup

CONFIG_PATH = Path("sources.json")
STATE_PATH = Path("data/state.json")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; DiscordNewsBot/1.0; +https://github.com)"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger("discord-news-bot")


def load_config() -> dict[str, Any]:
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "sources.json tidak ditemukan atau formatnya salah."
        ) from exc

    if not isinstance(data, dict) or "settings" not in data:
        raise RuntimeError("Struktur sources.json tidak valid (wajib ada key 'settings').")

    return data


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"sent_ids": []}

    try:
        with STATE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("state.json rusak atau kosong. Riwayat dimulai ulang.")
        return {"sent_ids": []}

    if not isinstance(data, dict):
        return {"sent_ids": []}

    data.setdefault("sent_ids", [])
    return data


def save_state(state: dict[str, Any], max_records: int) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["sent_ids"] = state.get("sent_ids", [])[-max_records:]

    with STATE_PATH.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def clean_text(value: str | None, limit: int = 900) -> str:
    if not value:
        return ""

    soup = BeautifulSoup(html.unescape(value), "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."

    return text


def normalize_url(url: str) -> str:
    return url.strip().replace("&amp;", "&")


def make_article_id(source_name: str, title: str, link: str) -> str:
    raw = f"{source_name}|{title.lower().strip()}|{link.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def entry_datetime(entry: Any) -> str:
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time:
        return datetime(*struct_time[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def extract_entry_image(entry: Any) -> str | None:
    media_content = entry.get("media_content", [])
    if isinstance(media_content, list):
        for item in media_content:
            if isinstance(item, dict) and item.get("url"):
                return normalize_url(str(item["url"]))

    media_thumbnail = entry.get("media_thumbnail", [])
    if isinstance(media_thumbnail, list):
        for item in media_thumbnail:
            if isinstance(item, dict) and item.get("url"):
                return normalize_url(str(item["url"]))

    enclosures = entry.get("enclosures", [])
    if isinstance(enclosures, list):
        for enclosure in enclosures:
            if not isinstance(enclosure, dict):
                continue
            enclosure_type = str(enclosure.get("type", ""))
            href = enclosure.get("href") or enclosure.get("url")
            if href and enclosure_type.startswith("image/"):
                return normalize_url(str(href))

    for field_name in ("summary", "description", "content"):
        value = entry.get(field_name)
        if isinstance(value, list):
            value = " ".join(
                str(item.get("value", "")) for item in value if isinstance(item, dict)
            )
        if isinstance(value, str):
            soup = BeautifulSoup(value, "html.parser")
            image = soup.find("img")
            if image and image.get("src"):
                return normalize_url(str(image["src"]))

    return None


def fetch_open_graph(link: str, timeout: int, user_agent: str) -> tuple[str | None, str | None]:
    if not link:
        return None, None

    try:
        response = requests.get(
            link,
            timeout=timeout,
            headers={"User-Agent": user_agent},
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.debug("Gagal mengambil metadata OpenGraph %s: %s", link, exc)
        return None, None

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type.lower():
        return None, response.url

    soup = BeautifulSoup(response.text, "html.parser")

    candidates = [
        soup.find("meta", property="og:image"),
        soup.find("meta", attrs={"name": "twitter:image"}),
        soup.find("meta", property="twitter:image"),
    ]

    for tag in candidates:
        if tag and tag.get("content"):
            return normalize_url(str(tag["content"])), response.url

    return None, response.url


def source_domain(link: str) -> str:
    try:
        return urlparse(link).netloc.removeprefix("www.")
    except ValueError:
        return "sumber berita"


def sanitize_webhook_url(url: str) -> str:
    # Sensor token Discord webhook agar tidak tercatat utuh di log error
    parts = url.split("/api/webhooks/")
    if len(parts) == 2:
        sub_parts = parts[1].split("/")
        if len(sub_parts) >= 2:
            return f"https://discord.com/api/webhooks/{sub_parts[0]}/[REDACTED]"
    return "https://discord.com/api/webhooks/[REDACTED]"


def mask_secrets(text: str, webhook_url: str) -> str:
    # Sensor token webhook jika muncul di dalam string exception requests
    if not webhook_url:
        return text
    parts = webhook_url.split("/api/webhooks/")
    if len(parts) == 2:
        sub_parts = parts[1].split("/")
        if len(sub_parts) >= 2:
            token = sub_parts[1].split("?")[0]
            if len(token) > 4:
                return text.replace(token, "[REDACTED]")
    return text


def parse_color(color_val: Any, default: int = 3447003) -> int:
    if isinstance(color_val, int):
        return max(0, min(color_val, 16777215))
    if isinstance(color_val, str):
        clean = color_val.strip()
        try:
            if clean.startswith("#"):
                return int(clean[1:], 16)
            if clean.lower().startswith("0x"):
                return int(clean, 16)
            return int(clean)
        except ValueError:
            return default
    return default


def parse_feed(
    source: dict[str, Any],
    timeout: int,
    feed_limit: int,
    user_agent: str,
) -> list[dict[str, Any]]:
    url = source.get("url", "")
    if not url:
        return []

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.error("Gagal mengambil feed %s: %s", source.get("name"), exc)
        return []

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        LOGGER.error(
            "Feed %s tidak dapat dibaca: %s",
            source.get("name"),
            getattr(feed, "bozo_exception", "format tidak valid"),
        )
        return []

    articles: list[dict[str, Any]] = []

    for entry in feed.entries[:feed_limit]:
        title = clean_text(entry.get("title"), 250)
        link = normalize_url(str(entry.get("link", "")))
        summary = clean_text(entry.get("summary") or entry.get("description"), 900)

        if not title or not link:
            continue

        image_url = extract_entry_image(entry)

        articles.append(
            {
                "source_name": source.get("name", "Unknown Source"),
                "title": title,
                "link": link,
                "summary": summary or "Buka tautan sumber untuk membaca berita selengkapnya.",
                "image_url": image_url,
                "published_at": entry_datetime(entry),
            }
        )

    return articles


def send_discord(
    webhook_url: str,
    channel_info: dict[str, Any],
    article: dict[str, Any],
    settings: dict[str, Any],
) -> bool:
    channel_label = channel_info.get("label", "News")
    embed_color = parse_color(channel_info.get("color", 3447003))
    retry_count = int(settings.get("discord_retry_count", 3))
    timeout = int(settings.get("request_timeout_seconds", 30))

    bot_name = (
        os.getenv("BOT_NAME")
        or settings.get("bot_name")
        or "Discord News Bot"
    )
    bot_avatar = (
        os.getenv("BOT_AVATAR_URL")
        or settings.get("bot_avatar_url")
        or ""
    )

    embed: dict[str, Any] = {
        "title": article["title"][:256],
        "url": article["link"],
        "description": article["summary"][:4096],
        "color": embed_color,
        "fields": [
            {
                "name": "Sumber",
                "value": article["source_name"][:1024],
                "inline": True,
            },
            {
                "name": "Kategori",
                "value": channel_label[:1024],
                "inline": True,
            },
        ],
        "footer": {
            "text": f"{source_domain(article['link'])} • Buka tautan untuk membaca sumber asli"[:2048]
        },
        "timestamp": article["published_at"],
    }

    if article.get("image_url"):
        embed["thumbnail"] = {"url": article["image_url"]}

    payload: dict[str, Any] = {
        "username": bot_name,
        "allowed_mentions": {"parse": []},
        "embeds": [embed],
    }
    if bot_avatar:
        payload["avatar_url"] = bot_avatar

    for attempt in range(1, retry_count + 1):
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=timeout,
            )

            if response.status_code in (200, 204):
                return True

            if response.status_code == 429:
                retry_after = 2.0
                try:
                    retry_after = float(response.json().get("retry_after", retry_after))
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass

                LOGGER.warning("Discord rate limit tercapai. Menunggu %.1f detik.", retry_after)
                time.sleep(retry_after)
                continue

            LOGGER.error(
                "Discord menolak pesan (%s): %s",
                response.status_code,
                response.text[:500],
            )
        except requests.RequestException as exc:
            safe_url = sanitize_webhook_url(webhook_url)
            safe_error = mask_secrets(str(exc), webhook_url)
            LOGGER.error(
                "Koneksi webhook %s percobaan %s/%s gagal: %s",
                safe_url,
                attempt,
                retry_count,
                safe_error,
            )

        if attempt < retry_count:
            time.sleep(attempt * 2)

    return False


def process_channel(
    channel_key: str,
    channel_info: dict[str, Any],
    settings: dict[str, Any],
    sent_ids: set[str],
    is_initial_run: bool = False,
) -> int:
    env_var_name = channel_info.get("webhook_env") or f"DISCORD_{channel_key.upper()}_WEBHOOK"
    webhook_url = os.getenv(env_var_name, "").strip()

    if not webhook_url:
        LOGGER.warning(
            "Channel '%s' dilewati: Environment variable %s belum disetel.",
            channel_key,
            env_var_name,
        )
        return 0

    sources = channel_info.get("sources", [])
    timeout = int(settings.get("request_timeout_seconds", 30))
    feed_limit = int(settings.get("feed_limit", 12))
    max_per_source = int(settings.get("max_posts_per_source_per_run", 3))
    max_per_channel = int(settings.get("max_posts_per_channel_per_run", 10))
    initial_count = int(settings.get("initial_send_count_per_source", 1))
    delay = float(settings.get("delay_between_messages_seconds", 1.5))
    fetch_thumbnail = bool(settings.get("fetch_thumbnail_from_article", True))
    seed_past = bool(settings.get("seed_past_articles_on_first_run", True))
    user_agent = settings.get("user_agent") or DEFAULT_USER_AGENT

    total_sent = 0

    for source in sources:
        if total_sent >= max_per_channel:
            break

        if not source.get("enabled", False):
            continue

        if source.get("type") != "rss":
            LOGGER.info("Sumber %s dilewati karena tipe bukan RSS.", source.get("name", "tanpa nama"))
            continue

        articles = parse_feed(source, timeout, feed_limit, user_agent)
        if not articles:
            continue

        new_articles: list[tuple[str, dict[str, Any]]] = []
        for article in articles:
            article_id = make_article_id(
                article["source_name"],
                article["title"],
                article["link"],
            )
            if article_id not in sent_ids:
                new_articles.append((article_id, article))

        if not new_articles:
            LOGGER.info("[%s] %s: tidak ada artikel baru.", channel_key, source.get("name"))
            continue

        per_source_limit = min(max_per_source, max_per_channel - total_sent)
        if is_initial_run:
            per_source_limit = min(per_source_limit, initial_count)

        # Feed biasanya urutan artikel terbaru dahulu; kirim dari yang paling lama ke yang baru
        selected = list(reversed(new_articles[:per_source_limit]))

        for article_id, article in selected:
            if fetch_thumbnail and not article.get("image_url"):
                image_url, resolved_url = fetch_open_graph(article["link"], timeout, user_agent)
                if image_url:
                    article["image_url"] = image_url
                if resolved_url:
                    article["link"] = resolved_url

            success = send_discord(
                webhook_url,
                channel_info,
                article,
                settings,
            )

            if success:
                sent_ids.add(article_id)
                total_sent += 1
                LOGGER.info("[%s] Terkirim: %s", channel_key, article["title"])
                time.sleep(delay)

            if total_sent >= max_per_channel:
                break

        # Pada run pertama, tandai sisa artikel lama sebagai sudah dibaca agar tidak terjadi banjir spam di run berikutnya
        if is_initial_run and seed_past:
            for article_id, _ in new_articles[per_source_limit:]:
                sent_ids.add(article_id)

    return total_sent


def main() -> None:
    config = load_config()
    settings = config.get("settings", {})
    state = load_state()
    sent_ids = set(state.get("sent_ids", []))
    is_initial_run = len(sent_ids) == 0

    if is_initial_run:
        LOGGER.info("Menjalankan initial run pertama kali (state kosong).")

    # Dukung struktur channels terpusat maupun legacy flat list
    raw_channels = config.get("channels")
    if not isinstance(raw_channels, dict):
        raw_channels = {}
        for key, val in config.items():
            if key != "settings" and isinstance(val, list):
                raw_channels[key] = {
                    "webhook_env": f"DISCORD_{key.upper()}_WEBHOOK",
                    "label": f"{key.capitalize()} News",
                    "sources": val,
                }

    total_sent = 0
    for channel_key, channel_info in raw_channels.items():
        if isinstance(channel_info, dict):
            total_sent += process_channel(
                channel_key,
                channel_info,
                settings,
                sent_ids,
                is_initial_run=is_initial_run,
            )

    state["sent_ids"] = list(sent_ids)
    save_state(state, int(settings.get("max_state_records", 3000)))

    LOGGER.info("Selesai. Total artikel terkirim di seluruh channel: %s", total_sent)


if __name__ == "__main__":
    main()
