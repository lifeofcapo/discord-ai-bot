import os
import logging

from dotenv import load_dotenv
load_dotenv()

from merchant_bot.bot import build_bot

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

logging.basicConfig(level=logging.INFO)


def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN haven't found"
        )
    if not GUILD_ID:
        raise RuntimeError("DISCORD_GUILD_ID haven't found .env.")

    bot = build_bot(guild_id=int(GUILD_ID))
    bot.run(TOKEN)


if __name__ == "__main__":
    main()