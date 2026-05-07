import os
import json
import urllib.request
import urllib.error
from pathlib import Path

DISCORD_API = "https://discord.com/api/v10"

def _load_token():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        hermes_env = Path.home() / ".hermes" / ".env"
        if hermes_env.exists():
            for line in hermes_env.read_text().splitlines():
                if line.startswith("DISCORD_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return token

def send_discord_message(channel_name: str, content: str = "", embed: dict = None) -> bool:
    """
    Send a message to a specific Discord channel using the bot token.
    Uses the REST API directly to avoid requiring a running bot instance.
    """
    token = _load_token()
    if not token:
        print("Warning: DISCORD_BOT_TOKEN not found.")
        return False

    # 1. Get channel ID from name (requires fetching all channels in the guild)
    # For simplicity, we assume the user might provide a channel ID or we look it up.
    # In this project, channel names are fairly stable.
    
    # First, get guilds
    def discord_req(path, data=None):
        method = "POST" if data else "GET"
        req = urllib.request.Request(
            f"{DISCORD_API}{path}",
            data=json.dumps(data).encode() if data else None,
            headers={
                "Authorization": f"Bot {token}",
                "User-Agent": "ArgusBot/1.0",
                "Content-Type": "application/json"
            },
            method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"Discord API Error {e.code}: {e.read().decode()}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    guilds = discord_req("/users/@me/guilds")
    if not guilds:
        return False

    # Find PV Workbench guild
    pv_guild = next((g for g in guilds if "pv" in g.get("name", "").lower() or "workbench" in g.get("name", "").lower()), guilds[0])
    
    # Get channels
    channels = discord_req(f"/guilds/{pv_guild['id']}/channels")
    if not channels:
        return False

    target_channel = next((c for c in channels if c.get("name") == channel_name), None)
    if not target_channel:
        print(f"Warning: Channel #{channel_name} not found.")
        return False

    # 2. Send message
    payload = {}
    if content: payload["content"] = content
    if embed: payload["embeds"] = [embed]

    result = discord_req(f"/channels/{target_channel['id']}/messages", payload)
    return result is not None
