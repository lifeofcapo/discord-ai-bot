import discord

from modals import ReservationModal, SaleSubmissionModal
from threads_utils import create_private_thread
import state


async def _get_existing_thread(interaction: discord.Interaction, thread_id: int) -> discord.Thread | None:
    """Проверяет, что тред из state реально ещё существует и не архивирован."""
    try:
        thread = await interaction.guild.fetch_channel(thread_id)
        if isinstance(thread, discord.Thread) and not thread.archived:
            return thread
    except (discord.NotFound, discord.Forbidden):
        pass
    return None


class MerchantAIView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🚀 Launch Merchant AI",
        style=discord.ButtonStyle.primary,
        custom_id="launch_merchant_ai",
    )
    async def launch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if state.is_on_cooldown(interaction.user.id, "merchant_ai"):
            await interaction.response.send_message(
                "Give it a second — your space is already being set up.", ephemeral=True
            )
            return

        existing_id = state.get_active_thread_id(interaction.user.id, "merchant_ai")
        if existing_id:
            existing = await _get_existing_thread(interaction, existing_id)
            if existing:
                await interaction.response.send_message(
                    f"You already have an open AI space: {existing.mention}",
                    ephemeral=True,
                )
                return
            else:
                state.clear_active_thread_id(interaction.user.id, "merchant_ai")

        thread = await create_private_thread(
            interaction,
            thread_name=f"AI Space — {interaction.user.display_name}",
        )

        state.register_ai_thread(thread.id)
        state.set_active_thread_id(interaction.user.id, "merchant_ai", thread.id)

        await thread.send(
            f"Welcome, {interaction.user.mention} 👋\n\n"
            "This is your private space to work with Merchant AI. "
            "Paste your conversation or send a screenshot, and I'll help you figure out the next move."
        )

        await interaction.response.send_message(
            f"Your private AI space is ready: {thread.mention}",
            ephemeral=True,
        )


class SupportCenterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Open Private Support Ticket",
        style=discord.ButtonStyle.secondary,
        custom_id="open_support_ticket",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if state.is_on_cooldown(interaction.user.id, "support"):
            await interaction.response.send_message(
                "Give it a second — your ticket is already being created.", ephemeral=True
            )
            return

        existing_id = state.get_active_thread_id(interaction.user.id, "support")
        if existing_id:
            existing = await _get_existing_thread(interaction, existing_id)
            if existing:
                await interaction.response.send_message(
                    f"You already have an open ticket: {existing.mention}",
                    ephemeral=True,
                )
                return
            else:
                state.clear_active_thread_id(interaction.user.id, "support")

        thread = await create_private_thread(
            interaction,
            thread_name=f"Ticket — {interaction.user.display_name}",
        )

        state.set_active_thread_id(interaction.user.id, "support", thread.id)

        await thread.send(
            f"Hi {interaction.user.mention}, describe your issue here and our team will get back to you shortly."
        )

        await interaction.response.send_message(
            f"Your private support ticket is ready: {thread.mention}",
            ephemeral=True,
        )


class ReserveBeatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Request Reservation",
        style=discord.ButtonStyle.primary,
        custom_id="request_reservation",
    )
    async def request(self, interaction: discord.Interaction, button: discord.ui.Button):
        if state.is_on_cooldown(interaction.user.id, "reserve"):
            await interaction.response.send_message(
                "Give it a second before submitting another request.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ReservationModal())


class SubmitSaleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Submit a Sale",
        style=discord.ButtonStyle.success,
        custom_id="submit_a_sale",
    )
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if state.is_on_cooldown(interaction.user.id, "submit_sale"):
            await interaction.response.send_message(
                "Give it a second before submitting another sale.", ephemeral=True
            )
            return
        await interaction.response.send_modal(SaleSubmissionModal())