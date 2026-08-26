import discord
from discord import app_commands
from discord.ext import commands

from .. import knowledge_base as kb
from ..permissions import is_authorized_admin


class KnowledgeBaseCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kb_add", description="[Admin] Добавить запись в базу знаний")
    @is_authorized_admin()
    @app_commands.describe(title="Короткое название", content="Полный текст правила/скрипта/кейса")
    async def kb_add(self, interaction: discord.Interaction, title: str, content: str):
        await interaction.response.defer(ephemeral=True)
        entry = await kb.add_entry(title, content, added_by=str(interaction.user))
        await interaction.followup.send(f"✅ Добавлено в базу знаний: **{entry.title}** (id: {entry.id})")

    @app_commands.command(name="kb_deactivate", description="[Admin] Деактивировать запись базы знаний по ID")
    @is_authorized_admin()
    async def kb_deactivate(self, interaction: discord.Interaction, entry_id: int):
        success = await kb.deactivate_entry(entry_id)
        if success:
            await interaction.response.send_message(f"✅ Запись {entry_id} деактивирована.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Запись с id {entry_id} не найдена.", ephemeral=True)

    @app_commands.command(name="kb_search", description="[Admin] Проверить, что найдёт база знаний по запросу")
    @is_authorized_admin()
    async def kb_search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        entries = await kb.search(query)
        if not entries:
            await interaction.followup.send("Ничего не найдено.")
            return
        lines = [f"**{e.title}** (id: {e.id})\n{e.content[:150]}..." for e in entries]
        await interaction.followup.send("\n\n".join(lines))


async def setup(bot: commands.Bot):
    await bot.add_cog(KnowledgeBaseCog(bot))