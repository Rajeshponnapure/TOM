# Instagram AI News Agent

Automatically scrolls your Instagram feed, extracts AI-related posts, generates a professional PDF report, and emails it to you on a schedule.

## Features

- 📱 **Instagram Feed Automation** — Logs in using your Chrome profile (no API key needed)
- 🤖 **AI Content Detection** — Filters posts for AI-related keywords (OpenAI, Claude, Anthropic, etc.)
- ⭐ **Smart Ranking** — Rates posts by importance (1-5 stars) based on keyword density
- 📊 **PDF Report** — Generates formatted PDF with summaries, ratings, and source links
- 📧 **Email Delivery** — Sends the report to your inbox with approval gate
- ⏰ **Scheduled Runs** — Runs every 3 hours automatically (configurable)

## Setup

### 1. Configure Environment Variables

For the canonical list of environment values and where to get them, see [../../ENVIRONMENT_SETUP_GUIDE.md](../../ENVIRONMENT_SETUP_GUIDE.md).

Copy `config.example.env` to `.env` and fill in your details:

```bash
cp config.example.env .env
```

Edit `.env`:
- Set `INSTAGRAM_CHROME_PROFILE` to your Chrome profile (usually "Default" or "Profile 1")
- Set `EMAIL_ADDRESS` to your Gmail or IMAP-compatible email
- Configure `GMAIL_CREDENTIALS_FILE` and `GMAIL_TOKEN_FILE` for OAuth email delivery

### 2. Gmail OAuth Setup (for email delivery)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create an OAuth 2.0 Desktop Client ID credentials
5. Download the credentials JSON file
6. Set `GMAIL_CREDENTIALS_FILE` in `.env` to the downloaded file path
7. First run will prompt you to authenticate via browser

### 3. Chrome Profile Setup

The agent uses your existing Chrome login session, so:
1. Make sure you're logged into Instagram in your Chrome browser
2. Find your profile name: `Settings → Profiles` in Chrome
3. Set `INSTAGRAM_CHROME_PROFILE` in `.env` to that profile name

### 4. Install Dependencies

```bash
# From the agent directory
pip install -r requirements.txt

# Or install globally in the main project
pip install reportlab apscheduler
```

## Usage

### Run Once

```bash
python main.py
```

This will:
1. Open Instagram using your Chrome profile
2. Scroll the feed and extract posts
3. Filter for AI-related content
4. Generate a PDF report
5. Ask for confirmation before emailing

### Run Continuously (Daemon)

```bash
python main.py --daemon
```

This runs the full workflow repeatedly using `INSTAGRAM_CHECK_INTERVAL_SECONDS`.

### TOM Controls

You can control the Instagram daemon from TOM commands:

- `Start instagram agent`
- `Stop instagram agent`
- `Instagram agent status`
- `Instagram agent summary`

### Run on Schedule (Every 3 Hours)

See [ARCHITECTURE.md](../../ARCHITECTURE.md) for integrating with the main TOM scheduler.

The scheduler can be configured in the main `agent.py` to call this agent every 3 hours.

## Output

Reports are saved to:
- PDF: `reports/instagram_ai_news_YYYY-MM-DD_HHMMSS.pdf`
- Log: Output appears in console and `tom_logs/safety_log.txt`

Each PDF includes:
- Report metadata (generated date/time)
- Summary statistics (high/medium/low importance counts)
- Detailed posts grouped by importance
- Author, rating, and source link for each post

## AI Keywords Detected

The agent filters for posts mentioning:
- Core: `ai`, `artificial intelligence`, `machine learning`, `openai`, `gpt`, `claude`, `anthropic`
- Companies: `meta ai`, `kimi`, `qwen`, `groq`, `ollama`, `hugging face`, `mistral`
- Techniques: `deep learning`, `neural network`, `llm`, `transformer`, `diffusion`, `rag`
- Applications: `chatgpt`, `generative ai`, `vision language`, `multimodal`

Add more keywords in `main.py` by editing the `AI_KEYWORDS` list.

## Architecture

```
InstagramAINNewsAgent
├── init_browser()          - Launch Chrome with your profile
├── open_instagram()        - Navigate to Instagram.com
├── scroll_feed()           - Scroll and extract post data
├── filter_ai_posts()       - Classify for AI relevance
├── generate_report()       - Create PDF via PDFReportGenerator
├── send_report_email()     - Email with approval gate
└── run_workflow()          - Orchestrate full pipeline
```

## Troubleshooting

**"Chrome profile not found"**
- Check profile name in `Settings → Profiles` in your Chrome browser
- Ensure you're using the exact name (case-sensitive)

**"Instagram didn't load"**
- Make sure you're logged into Instagram in that Chrome profile
- Try opening Instagram manually in Chrome to verify it works

**"No posts extracted"**
- Instagram may have blocked the scrolling automation
- Try running during off-peak hours
- Check that Instagram isn't showing error messages

**"Email not sending"**
- Verify `GMAIL_CREDENTIALS_FILE` path is correct
- Check your Gmail account allows third-party app access
- Look for authentication prompts in the console

## Configuration Options

In `.env`:
- `INSTAGRAM_POSTS_PER_RUN` — Number of posts to target (default: 50)
- `INSTAGRAM_SCROLL_PAUSE_TIME` — Seconds between scrolls (default: 2.0)
- `INSTAGRAM_MAX_SCROLL_ATTEMPTS` — Max scrolls before stopping (default: 100)
- `INSTAGRAM_CHECK_INTERVAL_SECONDS` — Daemon interval in seconds (default: 10800 / 3 hours)
- `INSTAGRAM_AUTO_SEND_REPORT_EMAIL` — Auto-send report emails without terminal prompt (`true`/`false`)

## Safety & Privacy

- ✅ No Instagram API key needed — uses your browser session
- ✅ No credentials stored — uses Chrome's own authentication
- ✅ Report emails can be approval-based or auto-send (`INSTAGRAM_AUTO_SEND_REPORT_EMAIL`)
- ✅ All actions logged to `tom_logs/safety_log.txt`

## Future Enhancements

- [ ] Save to Google Drive or OneDrive
- [ ] Filter by hashtags or accounts
- [ ] Image embedding in PDF
- [ ] Slack/Discord notifications
- [ ] Instagram Reels support
- [ ] Comment thread extraction

---

Built with ❤️ by TOM (The Omniscient Monitor)
