import discord
from discord import app_commands
from discord.ext import commands

from ..config import PARTNER_CATALOG_LIVE_ROLE, STAFF_ROLE_NAMES
from ..db import repository as db

# Роли, которые вообще не показываем в профиле (служебные/неинформативные)
HIDDEN_FROM_PROFILE = {"@everyone", PARTNER_CATALOG_LIVE_ROLE, "Staff Access"}


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Показать профиль мерчанта")
    @app_commands.describe(member="Чей профиль показать (по умолчанию — свой)")
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        role_names = {r.name for r in target.roles}

        visible_roles = [r.name for r in target.roles if r.name not in HIDDEN_FROM_PROFILE]
        visible_roles.sort()

        is_staff = bool(role_names.intersection(STAFF_ROLE_NAMES))
        has_live_catalog = PARTNER_CATALOG_LIVE_ROLE in role_names

        embed = discord.Embed(
            title=f"Merchant Profile — {target.display_name}",
            color=discord.Color.gold() if is_staff else discord.Color.dark_gold(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(
            name="Roles",
            value=", ".join(visible_roles) if visible_roles else "No roles yet",
            inline=False,
        )
        embed.add_field(
            name="Partner Catalog Live Access",
            value="✅ Approved" if has_live_catalog else "❌ Not yet approved",
            inline=True,
        )
        embed.add_field(
            name="Member Since",
            value=discord.utils.format_dt(target.joined_at, style="D") if target.joined_at else "Unknown",
            inline=True,
        )

        thread_record = await db.get_active_thread(target.id, "merchant_ai")
        if thread_record:
            history = await db.get_history(thread_record.id)
            embed.add_field(
                name="Merchant AI",
                value=f"Active space — {len(history)} messages on record",
                inline=False,
            )
        else:
            embed.add_field(name="Merchant AI", value="No active space yet", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=(member is None))


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))