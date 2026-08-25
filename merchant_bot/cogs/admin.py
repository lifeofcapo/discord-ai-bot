import discord
from discord import app_commands
from discord.ext import commands

from ..ui.views import MerchantAIView, SupportCenterView, ReserveBeatView, SubmitSaleView
from ..permissions import is_authorized_admin


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="post_merchant_ai_button",
        description="[Admin] Опубликовать кнопку Launch Merchant AI в этом канале",
    )
    @is_authorized_admin()
    async def post_merchant_ai_button(self, interaction: discord.Interaction):
        await interaction.channel.send(
            "**Merchant AI — Your Personal Sales Assistant**\n\n"
            "Stuck in a conversation with a client? Hit the button below to open your private AI space.",
            view=MerchantAIView(),
        )
        await interaction.response.send_message("Опубликовано ✅", ephemeral=True)

    @app_commands.command(
        name="post_support_button",
        description="[Admin] Опубликовать кнопку поддержки в этом канале",
    )
    @is_authorized_admin()
    async def post_support_button(self, interaction: discord.Interaction):
        await interaction.channel.send(
            "**Need Help?**\n\nOpen a private ticket and our team will get back to you.",
            view=SupportCenterView(),
        )
        await interaction.response.send_message("Опубликовано ✅", ephemeral=True)

    @app_commands.command(
        name="post_reserve_button",
        description="[Admin] Опубликовать кнопку резервации в этом канале",
    )
    @is_authorized_admin()
    async def post_reserve_button(self, interaction: discord.Interaction):
        await interaction.channel.send(
            "**Reserve a Beat**\n\nSubmit a reservation request for staff review.",
            view=ReserveBeatView(),
        )
        await interaction.response.send_message("Опубликовано ✅", ephemeral=True)

    @app_commands.command(
        name="post_submit_sale_button",
        description="[Admin] Опубликовать кнопку отправки продажи в этом канале",
    )
    @is_authorized_admin()
    async def post_submit_sale_button(self, interaction: discord.Interaction):
        await interaction.channel.send(
            "**Submit a Sale**\n\nLog a completed sale for staff processing.",
            view=SubmitSaleView(),
        )
        await interaction.response.send_message("Опубликовано ✅", ephemeral=True)

    @app_commands.command(
        name="list_threads",
        description="[Admin] Показать активные приватные треды в этом канале",
    )
    @is_authorized_admin()
    async def list_threads(self, interaction: discord.Interaction):
        threads = [
            t for t in interaction.channel.threads
            if t.type == discord.ChannelType.private_thread
        ]

        if not threads:
            await interaction.response.send_message("Активных тредов здесь нет.", ephemeral=True)
            return

        lines = [f"`{t.id}` — {t.name}" for t in threads]
        await interaction.response.send_message(
            "**Активные треды:**\n" + "\n".join(lines), ephemeral=True
        )

    @app_commands.command(
        name="close_thread",
        description="[Admin] Удалить тред по ID (работает, даже если вы не участник)",
    )
    @is_authorized_admin()
    @app_commands.describe(thread_id="ID треда — взять из /list_threads")
    async def close_thread(self, interaction: discord.Interaction, thread_id: str):
        try:
            thread = await self.bot.fetch_channel(int(thread_id))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("Тред с таким ID не найден.", ephemeral=True)
            return

        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message("Это не тред.", ephemeral=True)
            return

        name = thread.name
        await thread.delete()
        await interaction.response.send_message(f"🗑️ Удалено: {name}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))