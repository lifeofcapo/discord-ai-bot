import discord
from discord import app_commands
from discord.ext import commands


class MiscCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Проверка, что бот жив и отвечает")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🏓 Pong! Бот на связи, задержка: {round(self.bot.latency * 1000)}мс",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCog(bot))