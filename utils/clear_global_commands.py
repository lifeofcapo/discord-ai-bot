import asyncio
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    tree.clear_commands(guild=None)  
    await tree.sync(guild=None)
    print("Global commands cleared.")
    await client.close()


asyncio.run(client.start(TOKEN))