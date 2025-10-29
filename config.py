# This file stores configuration variables for the Discord bot.
import os

# IMPORTANT: Replace "YOUR_DISCORD_BOT_TOKEN" with your actual bot token.
# Keep this token secret and do not share it publicly.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "ODkyMjgwNDU1MDMyODc3MDk2.Gqo0zu.NXWO6nLKOUTYFqWPgxAJioHVW0cHjCdm0gqVgk")

# Google Gemini API key for chat responses. Set this to your real key.
# Example: GEMINI_API_KEY = "AIza..."
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAg8oDX2g9pZn9bPii0T_egz03bNrS9s7g")

# You can add other API keys here as needed.
# For example:
# SFW_API_KEY = "YOUR_SFW_API_KEY"
# NSFW_API_KEY = "YOUR_NSFW_API_KEY"

# Spotify API credentials for music features
# Create an app at https://developer.spotify.com/dashboard and paste values here
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "903cd357554042519ecbcacf1a3cd9d0")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "afb77c3260884572992551ad7d02cb4a")

# Optional: Path to ffmpeg executable. If empty, assumes ffmpeg is in PATH.
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "C:\\Users\\devan\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.0-full_build\\bin\\ffmpeg.exe")
# Bot owner user ID (Discord). If set (>0), only this user can change persona.
# Enable Developer Mode in Discord, right-click your profile → Copy User ID.
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "733972245575237632"))

# Lavalink configuration (for full-length music playback)
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "lavalink.jirayu.net")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "13592"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")


# Hardcoded global persona (system prompt) applied everywhere.
# Set a non-empty string to lock persona globally and disable !persona updates.
# Example: GLOBAL_PERSONA = "You are a concise, witty assistant focused on code."
GLOBAL_PERSONA = (
    "You are Discord AI chatbot. Built and Developed by Interact Developments Inc., "
    "their main website is https://interactdevelopments.me/. They have been operating since 2019 "
    "and have been creating Discord bots for a long time. "
    "You were initially a music bot from 2019-2023 but after 2 years of development you are a full-fledged "
    "Discord AI chatbot. Your main goal is to create a persona for your users to make them happy and keep "
    "them engaged. Keep the conversation cool and keep them hooked, like a close friend. "
    "Remember key details for 7 days and make the user feel homely and safe around you."
)

# OpenRouter configuration for image generation
# Set your OpenRouter API key to enable image generation via OpenRouter
# Example: OPENROUTER_API_KEY = "or-..."
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

# Optional: identify your site/app per OpenRouter guidelines
# Provide either a full URL for HTTP_REFERER, or leave blank
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "Discord Bot")

# Default OpenRouter image model; user requested Gemini 2.5 Flash Image (Nano Banana)
# Model id (as of now): google/gemini-2.5-flash-image-preview
OPENROUTER_IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview")

# -----------------------------------------------
# Bot Presence / Activity configuration
# Change these to control the bot's Discord status
# STATUS options: "online", "idle", "dnd", "invisible"
# ACTIVITY_TYPE options: "listening", "playing", "watching", "competing", "streaming", "none"
# For streaming, optionally set ACTIVITY_STREAM_URL (Twitch/YouTube URL)
BOT_STATUS = os.getenv("BOT_STATUS", "online")
ACTIVITY_TYPE = os.getenv("ACTIVITY_TYPE", "playing")
ACTIVITY_NAME = os.getenv("ACTIVITY_NAME", "/chat")
ACTIVITY_STREAM_URL = os.getenv("ACTIVITY_STREAM_URL", "")