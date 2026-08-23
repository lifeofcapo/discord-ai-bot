import discord

from modals import ReservationModal, SaleSubmissionModal
from threads_utils import create_private_thread
from state import register_ai_thread


class MerchantAIView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent — work after bot restart

    @discord.ui.button(
        label="Launch Merchant AI",
        style=discord.ButtonStyle.primary,
        custom_id="launch_merchant_ai",  # must be for persistent view
    )
    async def launch(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread = await create_private_thread(
            interaction,
            thread_name=f"AI Space — {interaction.user.display_name}",
        )

        register_ai_thread(thread.id)

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
        thread = await create_private_thread(
            interaction,
            thread_name=f"Ticket — {interaction.user.display_name}",
        )

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
        await interaction.response.send_modal(SaleSubmissionModal())