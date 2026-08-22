import os
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

from views import MerchantAIView, SupportCenterView, ReserveBeatView, SubmitSaleView

# --- Настройка ---
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("merchant-bot")

#Intents: needs for viewing content and participants
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    # registering persistent views — without it the buttons won't work after restart
    client.add_view(MerchantAIView())
    client.add_view(SupportCenterView())
    client.add_view(ReserveBeatView())
    client.add_view(SubmitSaleView())
    guild = discord.Object(id=GUILD_ID)
    tree.copy_global_to(guild=guild)
    synced = await tree.sync(guild=guild)

    log.info(f"Бот вошёл в систему как {client.user} (id: {client.user.id})")
    log.info(f"Синхронизировано команд на сервере: {len(synced)}")


@tree.command(name="post_merchant_ai_button", description="[Admin] Опубликовать кнопку Launch Merchant AI в этом канале")
@app_commands.checks.has_permissions(administrator=True)
async def post_merchant_ai_button(interaction: discord.Interaction):
    await interaction.channel.send(
        "**Merchant AI — Your Personal Sales Assistant**\n\n"
        "Stuck in a conversation with a client? Hit the button below to open your private AI space.",
        view=MerchantAIView(),
    )
    await interaction.response.send_message("Опубликовано ✅", ephemeral=True)


@tree.command(name="post_support_button", description="[Admin] Опубликовать кнопку поддержки в этом канале")
@app_commands.checks.has_permissions(administrator=True)
async def post_support_button(interaction: discord.Interaction):
    await interaction.channel.send(
        "**Need Help?**\n\nOpen a private ticket and our team will get back to you.",
        view=SupportCenterView(),
    )
    await interaction.response.send_message("Опубликовано ✅", ephemeral=True)


@tree.command(name="post_reserve_button", description="[Admin] Опубликовать кнопку резервации в этом канале")
@app_commands.checks.has_permissions(administrator=True)
async def post_reserve_button(interaction: discord.Interaction):
    await interaction.channel.send(
        "**Reserve a Beat**\n\nSubmit a reservation request for staff review.",
        view=ReserveBeatView(),
    )
    await interaction.response.send_message("Опубликовано ✅", ephemeral=True)


@tree.command(name="post_submit_sale_button", description="[Admin] Опубликовать кнопку отправки продажи в этом канале")
@app_commands.checks.has_permissions(administrator=True)
async def post_submit_sale_button(interaction: discord.Interaction):
    await interaction.channel.send(
        "**Submit a Sale**\n\nLog a completed sale for staff processing.",
        view=SubmitSaleView(),
    )
    await interaction.response.send_message("Опубликовано ✅", ephemeral=True)


@tree.command(name="ping", description="Проверка, что бот жив и отвечает")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏓 Pong! Бот на связи, задержка: {round(client.latency * 1000)}мс",
        ephemeral=True, 
    )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN не найден. Скопируйте .env.example в .env и вставьте токен."
        )
    client.run(TOKEN)