# Discord News Bot Template (GitHub Actions + RSS)

Automated, serverless Discord news bot that scrapes RSS feeds and broadcasts new articles to designated Discord channels via Webhooks using GitHub Actions.

Zero server hosting required. Powered entirely by GitHub Actions free tier.

---

## Features

- **100% Serverless**: Runs completely on GitHub Actions scheduled cron jobs. No VPS or continuous server uptime required.
- **Multi-Channel & Multi-Category**: Streamline Gaming, Tech, Crypto, or custom news categories to separate Discord channels.
- **Smart Deduplication**: Uses SHA-256 hashing to track sent articles in `data/state.json`, preventing duplicate messages across runs.
- **Rich Embeds & Visuals**: Extracts cover images directly from RSS media tags or resolves OpenGraph/Twitter card images via web scraping.
- **Discord Rate-Limit Handling**: Automatically parses and respects Discord's HTTP 429 `retry_after` header.
- **Privacy & Security**: Webhook URLs are managed strictly via GitHub Repository Secrets and masked in console logs.

---

## Project Structure

```text
discord-news-bot-template/
├── .github/
│   └── workflows/
│       └── discord-news.yml   # GitHub Actions scheduled workflow
├── data/
│   └── state.json             # Persistent state of processed article hashes
├── .env.example               # Template environment variables for local testing
├── .gitignore                 # Standard git ignores (secrets, venvs, caches)
├── bot.py                     # Core scraping, hashing, and Discord webhook dispatch logic
├── LICENSE                    # MIT License
├── requirements.txt           # Python dependencies
├── README.md                  # Documentation and setup guide
└── sources.json               # RSS feed sources and bot configuration
```

---

## Quick Start (5-Minute Setup)

### 1. Create a Repository from this Template
Click the green **"Use this template"** button at the top of this repository, then select **"Create a new repository"**.

### 2. Create Discord Webhook(s)
1. In your Discord server, open **Server Settings** -> **Integrations** -> **Webhooks**.
2. Click **New Webhook**, name it (e.g., `Gaming News`), and select the target channel.
3. Click **Copy Webhook URL**.
4. Repeat if you want separate webhooks for other categories (e.g., `Tech News`).

### 3. Add GitHub Repository Secrets
1. In your new GitHub repository, navigate to **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Add the following secrets matching your Discord Webhooks:
   - `DISCORD_GAMING_WEBHOOK`: Paste your gaming channel webhook URL.
   - `DISCORD_TECH_WEBHOOK`: Paste your tech channel webhook URL.

> **Note**: If you only use one category or add new ones, make sure the secret names match the `webhook_env` values defined in `sources.json`.

### 4. Enable Workflow Read & Write Permissions
GitHub Actions needs permission to commit `data/state.json` back to the repository:
1. Go to **Settings** -> **Actions** -> **General**.
2. Scroll to **Workflow permissions**.
3. Select **"Read and write permissions"** and check **"Allow GitHub Actions to create and approve pull requests"**.
4. Click **Save**.

### 5. Test Run & Enable Schedule
1. Go to the **Actions** tab in your repository.
2. Select **"Discord News Aggregator"** from the left sidebar.
3. Click **Run workflow** -> **Run workflow** to test it immediately. Check your Discord channels for new messages!
4. To enable automated runs every hour, open `.github/workflows/discord-news.yml`, uncomment the schedule line, and commit the changes:
   ```yaml
   schedule:
     - cron: "15 * * * *"
   ```

---

## Configuration (`sources.json`)

All bot configurations and RSS feed sources are managed inside `sources.json`.

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
    "fetch_thumbnail_from_article": true
  }
}
```

### Adding or Modifying Channels

Each channel under `"channels"` links to a specific webhook environment variable:

```json
"channels": {
  "crypto": {
    "webhook_env": "DISCORD_CRYPTO_WEBHOOK",
    "label": "Crypto News",
    "color": 16753920,
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

When adding a new channel, simply create the matching secret (e.g. `DISCORD_CRYPTO_WEBHOOK`) under repository secrets and update `.github/workflows/discord-news.yml` to inject it into the runner environment.

---

## Local Development

To test the bot locally on your machine:

1. Clone your repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Setup environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and paste your actual Discord Webhook URLs
   ```

4. Run the scraper:
   ```bash
   python bot.py
   ```

---

## How State Persistence Works (Git Scraping)

GitHub Actions runners are ephemeral (destroyed when the job finishes). To avoid resending articles every run, `bot.py` keeps a rolling list of processed article SHA-256 hashes in `data/state.json`.

At the end of each workflow execution:
1. `bot.py` updates `data/state.json`.
2. Git checks for modifications (`git diff --cached --quiet`).
3. If new articles were sent, the runner commits and pushes `data/state.json` back to `main` with `[skip ci]` to prevent infinite workflow loops.

---

## Contributing

Contributions, feed suggestions, and improvements are welcome! Feel free to open an Issue or submit a Pull Request.

---

## License

This project is open-source and available under the [MIT License](LICENSE).
