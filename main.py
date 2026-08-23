import os
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

from views import MerchantAIView, SupportCenterView, ReserveBeatView, SubmitSaleView
from ai_client import get_ai_response, build_user_content
import state

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("merchant-bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
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
        "**Merchant AI**\n\n"
        "Need help with a deal? Open your private AI Space below.",
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


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    thread_id = message.channel.id

    # answer only in AI placement
    if not state.is_ai_thread(thread_id):
        return

    image_urls = [
        att.url for att in message.attachments
        if att.content_type and att.content_type.startswith("image/")
    ]

    user_content = build_user_content(message.content, image_urls)
    state.append_message(thread_id, "user", user_content)

    async with message.channel.typing():
        try:
            reply = await get_ai_response(state.get_history(thread_id))
        except Exception as e:
            log.error(f"OpenAI error: {e}")
            await message.channel.send(
                "⚠️ Something went wrong while generating a response. Please try again in a moment."
            )
            return

    state.append_message(thread_id, "assistant", reply)
    await message.channel.send(reply)


@tree.command(name="reset", description="Сбросить память и историю в этом AI-пространстве")
async def reset(interaction: discord.Interaction):
    thread_id = interaction.channel.id

    if not state.is_ai_thread(thread_id):
        await interaction.response.send_message(
            "Эта команда работает только внутри приватного AI-пространства.",
            ephemeral=True,
        )
        return

    state.reset_thread(thread_id)
    await interaction.response.send_message(
        "🔄 Память сброшена. Можно начинать с чистого листа.",
    )


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