# Deploy to Render (24/7 Worker)

This project is configured to run as a Render Worker so the Discord bot stays online 24/7.

## Prerequisites
- A Render account
- Your Discord bot token and any API keys (do NOT commit secrets)

## Files added
- `render.yaml` – Render Blueprint defining a Python Worker
- `apt.txt` – Requests `ffmpeg` installation (for music/audio)
- `config.py` – Reads configuration from environment variables if present

## One‑click with Blueprint
1. Push this repository to your own GitHub.
2. In Render, click New → Blueprint.
3. Paste your repo URL. Render will read `render.yaml`.
4. In the generated service, set these environment variables:
   - `DISCORD_TOKEN` (required)
   - `GEMINI_API_KEY` (optional)
   - `OPENROUTER_API_KEY` (optional)
   - `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` (optional)
   - `OWNER_USER_ID` (optional)
   - `FFMPEG_PATH` = `/usr/bin/ffmpeg`
   - Presence controls (optional): `BOT_STATUS`, `ACTIVITY_TYPE`, `ACTIVITY_NAME`, `ACTIVITY_STREAM_URL`
5. Select at least the Starter plan for the Worker to run continuously.
6. Deploy.

## Commands
- Build: `pip install -r requirements.txt`
- Start: `python -u main.py`

## Notes
- Free plan services may sleep/stop; use Starter or above for true 24/7 workers.
- Secrets are read from env vars at runtime; local defaults in `config.py` are only for development.
