<p align="center">
  <img src="./.github/assets/logo.png" alt="Discord News Bot Template Logo" width="160" />
</p>

<h1 align="center">Discord News Bot Template</h1>

<p align="center">
  A serverless Discord news aggregation bot that scrapes RSS feeds and delivers formatted news updates to Discord channels via Webhooks using GitHub Actions.
</p>

<p align="center">
  <a href="https://github.com/idabagusweda/discord-news-bot-template/generate">Use this Template</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/idabagusweda/discord-news-bot-template/issues">Report an Issue</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" />
  <img alt="GitHub Actions" src="https://img.shields.io/badge/GitHub_Actions-Automated-2088FF?logo=githubactions&logoColor=white" />
  <img alt="Discord" src="https://img.shields.io/badge/Discord-Webhooks-5865F2?logo=discord&logoColor=white" />
  <img alt="RSS" src="https://img.shields.io/badge/RSS-Feedparser-FFA500?logo=rss&logoColor=white" />
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" /></a>
</p>

---

## Overview

**Discord News Bot Template** provides an automated, serverless architecture for broadcasting curated news feeds directly to your Discord server channels. It retrieves content from RSS feeds, extracts rich metadata and article thumbnails, checks for duplicate articles, and posts embeds to designated Discord webhooks on a customizable schedule.

The entire workflow executes on GitHub Actions runners without requiring a 24/7 VPS, dedicated server, or database subscription. Article state is tracked using a Git-as-a-database pattern, persisting sent article IDs directly in the repository between runs.

---

## Features

### Scraping and Content Delivery

- **Multi-source RSS parsing:** Scrapes multiple RSS feeds per category concurrently with configurable per-run limits.
- **Smart deduplication:** Calculates SHA-256 hashes (`source_name|title|link`) to track sent articles in `data/state.json`, preventing duplicate messages across runs.
- **First-run spam protection:** Automatically seeds historical feed entries on initial run, sending only one verification post per source to avoid flooding Discord channels.
- **Image and OpenGraph resolution:** Extracts article cover images from RSS enclosures, media thumbnails, or scrapes fallback OpenGraph (`og:image`) and Twitter Card metadata.
- **Chronological ordering:** Publishes articles in chronological sequence (oldest to newest) to maintain natural feed reading order.

### Discord Webhook Integration

- **Multi-channel routing:** Route distinct categories (e.g., Gaming, Tech, Crypto) to independent Discord channels using category-specific webhooks.
- **Customizable Rich Embeds:** Embeds include source attribution, category tags, timestamp, clean description text, and source domain footer.
- **Embed color customization:** Set custom embed sidebar colors per channel using hex strings (`#5865F2`) or integer values.
- **Rate-limit compliance:** Automatically catches HTTP 429 responses, extracts Discord's `retry_after` window, and pauses execution before retrying.

### Reliability and Security

- **Zero server maintenance:** 100% automated using GitHub Actions scheduled cron workflows.
- **Secret protection:** Discord Webhook URLs are managed strictly through GitHub Repository Secrets.
- **Error log sanitization:** Built-in `mask_secrets()` strips sensitive webhook tokens from exception stack traces and log messages.
- **Automatic rebase strategy:** GitHub Actions utilizes `git pull --rebase -X theirs origin main` to resolve concurrent state updates without workflow crashes.

---

## Technology Stack

| Area                     | Technology                                    |
| ------------------------ | --------------------------------------------- |
| CI/CD & Automation       | GitHub Actions (`ubuntu-latest` runner)       |
| Programming Language     | Python 3.12+                                  |
| Feed Parsing             | `feedparser` 6.x                              |
| HTTP & Network           | `requests` 2.x                                |
| HTML & Metadata Scraping | `BeautifulSoup4`                              |
| State & Persistence      | SHA-256 Hashing, Git-as-a-database            |
| Configuration Format     | JSON (`sources.json`)                         |
| Environment Management   | `python-dotenv` 1.x, GitHub Repository Secrets|
| Licensing                | MIT License                                   |

---

## Getting Started

### Prerequisites

- A GitHub account.
- A Discord server with permissions to manage Webhooks.
- Python 3.10 or later (only required for local testing).

---

### Step 1: Create a Repository from this Template

1. Click the **[Use this template](https://github.com/idabagusweda/discord-news-bot-template/generate)** button at the top of this repository.
2. Enter your desired repository name (e.g., `my-discord-news-bot`).
3. Select **Public** or **Private**.
4. Click **Create repository**.

---

### Step 2: Create Discord Webhooks

1. Open your Discord server and navigate to the target text channel.
2. Click the channel **Settings** gear icon -> **Integrations** -> **Webhooks**.
3. Click **New Webhook**, assign a name (e.g., `Gaming News`), and ensure the correct channel is selected.
4. Click **Copy Webhook URL**.
5. Repeat this step for each channel you wish to route news into (e.g., `Tech News`).

---

### Step 3: Configure GitHub Repository Secrets

1. In your new GitHub repository, navigate to **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Create the secrets corresponding to the channels configured in `sources.json`:

| Secret Name              | Value                                         |
| ------------------------ | --------------------------------------------- |
| `DISCORD_GAMING_WEBHOOK` | Paste the webhook URL for your gaming channel |
| `DISCORD_TECH_WEBHOOK`   | Paste the webhook URL for your tech channel   |

> **Note:** If you add custom categories (e.g., Crypto), add a matching secret (e.g., `DISCORD_CRYPTO_WEBHOOK`) as defined in `sources.json`.

---

### Step 4: Configure GitHub Actions Workflow Permissions

GitHub Actions requires write permissions to commit `data/state.json` back to your repository:

1. In your repository, go to **Settings** -> **Actions** -> **General**.
2. Scroll down to **Workflow permissions**.
3. Select **Read and write permissions**.
4. Check **Allow GitHub Actions to create and approve pull requests**.
5. Click **Save**.

---

### Step 5: Test Run and Enable Schedule

1. Go to the **Actions** tab in your GitHub repository.
2. Select **Discord News Aggregator** from the left workflow sidebar.
3. Click **Run workflow** -> select branch `main` -> click **Run workflow**.
4. Check your Discord channels. Verification articles should arrive within seconds.
5. To activate automated scheduled runs, open `.github/workflows/discord-news.yml`, uncomment the `schedule` block, and commit changes:

```yaml
on:
  workflow_dispatch:
  schedule:
    # Run every hour at minute 15
    - cron: "15 * * * *"
```

---

## Environment Variables

### Repository Secrets & Local `.env`

| Variable                 | Required | Description                                                         |
| ------------------------ | -------- | ------------------------------------------------------------------- |
| `DISCORD_GAMING_WEBHOOK` | Yes*     | Webhook URL for the gaming category channel.                        |
| `DISCORD_TECH_WEBHOOK`   | Yes*     | Webhook URL for the tech category channel.                          |
| `BOT_NAME`               | No       | Custom username override for Discord webhook messages.             |
| `BOT_AVATAR_URL`         | No       | Custom avatar image URL override for Discord webhook messages.      |

*\* Only required if the corresponding channel is enabled in `sources.json`.*

> **Security Reminder:** Never commit your actual webhook URLs or `.env` files to git. Webhook tokens grant permission to post directly to your Discord server.

---

## Configuration (`sources.json`)

All operational parameters and RSS feeds are configured in `sources.json`.

### Global Settings

```json
{
  "settings": {
    "bot_name": "News Aggregator Bot",
    "bot_avatar_url": "",
    "user_agent": "Mozilla/5.0 (compatible; DiscordNewsBot/1.0)",
    "request_timeout_seconds": 30,
    "feed_limit": 12,
    "initial_send_count_per_source": 1,
    "max_posts_per_source_per_run": 3,
    "max_posts_per_channel_per_run": 10,
    "discord_retry_count": 3,
    "delay_between_messages_seconds": 1.5,
    "max_state_records": 3000,
    "fetch_thumbnail_from_article": true,
    "seed_past_articles_on_first_run": true
  }
}
```

### Adding a Custom Channel Category

You can add any new category under `"channels"` without modifying the Python source code:

```json
"channels": {
  "crypto": {
    "webhook_env": "DISCORD_CRYPTO_WEBHOOK",
    "label": "Crypto News",
    "color": "#F7931A",
    "sources": [
      {
        "name": "CoinDesk",
        "type": "rss",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "site_url": "https://www.coindesk.com",
        "language": "en",
        "enabled": true
      }
    ]
  }
}
```

After adding a new channel category:
1. Add `DISCORD_CRYPTO_WEBHOOK` to your GitHub Repository Secrets.
2. In `.github/workflows/discord-news.yml`, map the environment variable to the step:
   ```yaml
   env:
     DISCORD_GAMING_WEBHOOK: ${{ secrets.DISCORD_GAMING_WEBHOOK }}
     DISCORD_TECH_WEBHOOK: ${{ secrets.DISCORD_TECH_WEBHOOK }}
     DISCORD_CRYPTO_WEBHOOK: ${{ secrets.DISCORD_CRYPTO_WEBHOOK }}
   ```

---

## Project Structure

```text
discord-news-bot-template/
├── .github/
│   ├── assets/
│   │   └── logo.png           # Project branding logo
│   └── workflows/
│       └── discord-news.yml   # Scheduled GitHub Actions automation workflow
├── data/
│   └── state.json             # Persistent rolling history of sent article IDs
├── .env.example               # Template environment variables for local testing
├── .gitignore                 # Standard Python, OS, and secret exclusions
├── bot.py                     # Main application logic (fetching, parsing, webhook)
├── LICENSE                    # MIT open-source license
├── README.md                  # Project documentation and guide
├── requirements.txt           # Python package dependencies
└── sources.json               # Channel definitions, settings, and RSS sources
```

---

## How State Persistence Works (Git-as-a-database)

GitHub Actions runners are ephemeral virtual machines destroyed after each run. To maintain state without an external database:

```text
[Scheduled Trigger]
         │
         ▼
[Read data/state.json] ──► [Fetch RSS Feeds]
                                 │
                                 ▼
                     [Filter: article_id not in sent_ids]
                                 │
                                 ▼
                     [Send Webhook Embed to Discord]
                                 │
                                 ▼
                     [Append article_id to state.json]
                                 │
                                 ▼
                     [Commit & Push data/state.json [skip ci]]
```

1. `bot.py` reads existing processed hashes from `data/state.json`.
2. As new articles are published to Discord, their hashes are appended to the set.
3. At the end of the run, `data/state.json` is updated and trimmed to `max_state_records`.
4. The workflow runs `git commit` and pushes with `[skip ci]` to prevent triggering another workflow run.

---

## Local Development

To run and debug the bot locally:

### 1. Clone your repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Set up a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and insert your test Discord Webhook URLs:

```env
DISCORD_GAMING_WEBHOOK=https://discord.com/api/webhooks/your/test/webhook
DISCORD_TECH_WEBHOOK=https://discord.com/api/webhooks/your/test/webhook
```

### 4. Execute the bot

```bash
python bot.py
```

---

## Testing

When customizing or testing modifications to the bot, verify the following core flows:

- **Missing environment variables:** Run `python bot.py` with an empty `.env`. The bot should log clean warnings for unconfigured webhooks and exit with status code `0` without crashing.
- **Feed format compatibility:** Ensure all added RSS feeds in `sources.json` return status `200` and contain valid `entries`.
- **Thumbnail resolution:** Confirm article embeds display cover images from either RSS media enclosures or OpenGraph scraping.
- **Rate-limit resilience:** Test with a low delay (`delay_between_messages_seconds: 0.1`) to verify HTTP 429 backoff handling.
- **State deduplication:** Run `python bot.py` twice consecutively. The second run should log `tidak ada artikel baru` (no new articles).

---

## Contributing

Contributions, feed recommendations, and improvements are welcome. To propose a change:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/my-improvement`.
3. Commit your changes: `git commit -m "feat: add feature description"`.
4. Push to your branch: `git push origin feat/my-improvement`.
5. Open a Pull Request with a clear description of the modifications.

---

## License

This project is distributed under the MIT License. See the [`LICENSE`](./LICENSE) file for details.

---

## Acknowledgements

This project utilizes open-source libraries and services:

- [feedparser](https://github.com/kurtmckee/feedparser) for RSS and Atom feed handling.
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing and metadata extraction.
- [requests](https://requests.readthedocs.io/) for HTTP communication.
- [python-dotenv](https://github.com/theskumar/python-dotenv) for local environment variable loading.
- [GitHub Actions](https://github.com/features/actions) for serverless scheduling and execution.
- [Discord Webhook API](https://discord.com/developers/docs/resources/webhook) for rich embed notifications.

---

<p align="center">
  <a href="https://github.com/idabagusweda">GitHub: @idabagusweda</a>
</p>
