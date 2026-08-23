import os
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

from views import MerchantAIView, SupportCenterView, ReserveBeatView, SubmitSaleView
from ai_client import get_ai_response, build_user_content
import state

# --- Настройка ---
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("merchant-bot")

# --- Intents: без этого бот не увидит контент сообщений и участников ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    # Регистрируем persistent views — без этого кнопки перестанут работать после рестарта бота
    client.add_view(MerchantAIView())
    client.add_view(SupportCenterView())
    client.add_view(ReserveBeatView())
    client.add_view(SubmitSaleView())

    # Синхронизация команд НА КОНКРЕТНЫЙ СЕРВЕР — применяется мгновенно,
    # в отличие от глобальной синхронизации (та может идти до часа)
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


@client.event
async def on_message(message: discord.Message):
    # Игнорируем сообщения от самого бота — иначе будет бесконечный цикл
    if message.author.bot:
        return

    thread_id = message.channel.id

    # Отвечаем только там, где реально запущено AI-пространство
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


@tree.command(name="list_threads", description="[Admin] Показать активные приватные треды в этом канале")
@app_commands.checks.has_permissions(administrator=True)
async def list_threads(interaction: discord.Interaction):
    threads = [t for t in interaction.channel.threads if t.type == discord.ChannelType.private_thread]

    if not threads:
        await interaction.response.send_message("Активных тредов здесь нет.", ephemeral=True)
        return

    lines = [f"`{t.id}` — {t.name}" for t in threads]
    await interaction.response.send_message(
        "**Активные треды:**\n" + "\n".join(lines), ephemeral=True
    )


@tree.command(name="close_thread", description="[Admin] Удалить тред по ID (работает, даже если вы не участник)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(thread_id="ID треда — взять из /list_threads")
async def close_thread(interaction: discord.Interaction, thread_id: str):
    try:
        thread = await client.fetch_channel(int(thread_id))
    except (ValueError, discord.NotFound):
        await interaction.response.send_message("Тред с таким ID не найден.", ephemeral=True)
        return

    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("Это не тред.", ephemeral=True)
        return

    name = thread.name
    await thread.delete()
    await interaction.response.send_message(f"🗑️ Удалено: {name}", ephemeral=True)


@tree.command(name="ping", description="Проверка, что бот жив и отвечает")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏓 Pong! Бот на связи, задержка: {round(client.latency * 1000)}мс",
        ephemeral=True,  # видно только тому, кто вызвал команду
    )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN не найден. Скопируйте .env.example в .env и вставьте токен."
        )
    client.run(TOKEN)