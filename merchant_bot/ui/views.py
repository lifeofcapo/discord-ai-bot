import discord

from .modals import ReservationModal, SaleSubmissionModal
from ..threads_utils import create_private_thread
from .. import state
from ..db import repository as db
from ..summarizer import close_thread_with_summary
from ..permissions import has_admin_role

MAX_ACTIVE_MERCHANT_AI_THREADS = 3


async def _get_existing_thread(interaction: discord.Interaction, thread_id: int) -> discord.Thread | None:
    try:
        thread = await interaction.guild.fetch_channel(thread_id)
        if isinstance(thread, discord.Thread) and not thread.archived:
            return thread
    except (discord.NotFound, discord.Forbidden):
        pass
    return None


class CloseThreadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Close this chat",
        style=discord.ButtonStyle.danger,
        custom_id="close_merchant_ai_thread",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread_id = interaction.channel.id

        thread_record = await db.get_thread(thread_id)
        if thread_record is None or thread_record.kind != "merchant_ai" or not thread_record.active:
            await interaction.response.send_message(
                "This chat is already closed.", ephemeral=True
            )
            return

        role_names = {r.name for r in interaction.user.roles}
        is_owner = interaction.user.id == thread_record.student_id
        is_staff = has_admin_role(role_names)

        if not is_owner and not is_staff:
            await interaction.response.send_message(
                "Only the person who opened this chat, or staff, can close it.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        await close_thread_with_summary(thread_id, thread_record.student_id)


        await interaction.followup.send(
            "🔒 Chat closed and removed. You can open a new one anytime.", ephemeral=True
        )

        try:
            await interaction.channel.delete()
        except discord.HTTPException:
            pass  # тред всё равно деактивирован в БД — не критично, если удаление в Discord не удалось


class MerchantAIView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Launch Merchant AI",
        style=discord.ButtonStyle.primary,
        custom_id="launch_merchant_ai",
    )
    async def launch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if state.is_on_cooldown(interaction.user.id, "merchant_ai"):
            await interaction.response.send_message(
                "Give it a second — your space is already being set up.", ephemeral=True
            )
            return

        await db.get_or_create_student(interaction.user.id, interaction.user.display_name)

        active_records = await db.get_active_threads(interaction.user.id, "merchant_ai")

        live_records = []
        for record in active_records:
            existing = await _get_existing_thread(interaction, record.id)
            if existing:
                live_records.append((record, existing))
            else:
                await db.deactivate_thread(record.id)

        if len(live_records) >= MAX_ACTIVE_MERCHANT_AI_THREADS:
            mentions = ", ".join(thread.mention for _, thread in live_records)
            await interaction.response.send_message(
                f"You've reached the limit of {MAX_ACTIVE_MERCHANT_AI_THREADS} open AI chats "
                f"at the same time: {mentions}\n\n"
                f"Close one first (use the 🔒 Close this chat button inside it) before starting a new one.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        thread = await create_private_thread(
            interaction,
            thread_name=f"AI Space — {interaction.user.display_name}",
        )

        await db.create_thread(thread.id, interaction.user.id, "merchant_ai")

        await thread.send(
            f"Welcome, {interaction.user.mention} 👋\n\n"
            "This is your private space to work with Merchant AI. "
            "Paste your conversation or send a screenshot, and I'll help you figure out the next move.\n\n"
            "When you're done, close this chat with the button below — you can always start a fresh one.",
            view=CloseThreadView(),
        )

        await interaction.followup.send(
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

        await db.get_or_create_student(interaction.user.id, interaction.user.display_name)

        existing_records = await db.get_active_threads(interaction.user.id, "support")
        existing_record = existing_records[0] if existing_records else None
        if existing_record:
            existing = await _get_existing_thread(interaction, existing_record.id)
            if existing:
                await interaction.response.send_message(
                    f"You already have an open ticket: {existing.mention}",
                    ephemeral=True,
                )
                return
            else:
                await db.deactivate_thread(existing_record.id)

        await interaction.response.defer(ephemeral=True)

        thread = await create_private_thread(
            interaction,
            thread_name=f"Ticket — {interaction.user.display_name}",
        )

        await db.create_thread(thread.id, interaction.user.id, "support")

        await thread.send(
            f"Hi {interaction.user.mention}, describe your issue here and our team will get back to you shortly."
        )

        await interaction.followup.send(
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