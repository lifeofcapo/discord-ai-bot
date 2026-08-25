import logging

import discord
from discord import app_commands
from discord.ext import commands

from .ui.views import MerchantAIView, SupportCenterView, ReserveBeatView, SubmitSaleView

log = logging.getLogger("merchant-bot")

COGS = [
    "merchant_bot.cogs.admin",
    "merchant_bot.cogs.ai_assistant",
    "merchant_bot.cogs.profile",
    "merchant_bot.cogs.misc",
]


class MerchantBot(commands.Bot):
    def __init__(self, guild_id: int):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents) 
        self.guild_id = guild_id

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)

        self.add_view(MerchantAIView())
        self.add_view(SupportCenterView())
        self.add_view(ReserveBeatView())
        self.add_view(SubmitSaleView())

        guild = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        log.info(f"Синхронизировано команд на сервере: {len(synced)}")

    async def on_ready(self):
        log.info(f"Бот вошёл в систему как {self.user} (id: {self.user.id})")


def build_bot(guild_id: int) -> MerchantBot:
    bot = MerchantBot(guild_id=guild_id)

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True
            )
            return
        log.error(f"Unhandled command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Something went wrong running that command.", ephemeral=True
            )

    return bot