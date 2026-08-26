import discord

from ..threads_utils import create_private_thread


class ReservationModal(discord.ui.Modal, title="Partner Catalog Reservation Request"):
    product_id = discord.ui.TextInput(label="Product ID", required=True)
    artist_name = discord.ui.TextInput(label="Artist Name / Handle", required=True)
    amount_paid = discord.ui.TextInput(label="Amount Paid", required=True)
    payment_method = discord.ui.TextInput(label="Payment Method", required=True)
    payment_reference = discord.ui.TextInput(
        label="Payment Reference / Transaction ID", required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        thread = await create_private_thread(
            interaction,
            thread_name=f"Reservation — {self.product_id.value} — {interaction.user.display_name}",
        )

        embed = discord.Embed(
            title="🎯 New Reservation Request",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Product ID", value=self.product_id.value, inline=False)
        embed.add_field(name="Artist Name / Handle", value=self.artist_name.value, inline=False)
        embed.add_field(name="Amount Paid", value=self.amount_paid.value, inline=True)
        embed.add_field(name="Payment Method", value=self.payment_method.value, inline=True)
        embed.add_field(
            name="Payment Reference / Transaction ID",
            value=self.payment_reference.value,
            inline=False,
        )
        embed.set_footer(text=f"Submitted by {interaction.user}")

        await thread.send(embed=embed)

        await interaction.followup.send(
            "Reservation request submitted. The beat is not reserved yet. "
            "Staff will verify current availability and payment before confirming the reservation.",
            ephemeral=True,
        )


class SaleSubmissionModal(discord.ui.Modal, title="Partner Catalog Sale Submission"):
    product_id = discord.ui.TextInput(label="Product ID", required=True)
    artist_name = discord.ui.TextInput(label="Artist Name / Handle", required=True)
    artist_email = discord.ui.TextInput(label="Artist Email", required=True)
    sale_amount = discord.ui.TextInput(label="Sale Amount", required=True)
    payment_info = discord.ui.TextInput(
        label="Payment Method & Reference",
        placeholder="e.g. Stripe — txn_12345",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        thread = await create_private_thread(
            interaction,
            thread_name=f"Sale — {self.product_id.value} — {interaction.user.display_name}",
        )

        embed = discord.Embed(
            title="💰 New Sale Submission",
            color=discord.Color.green(),
        )
        embed.add_field(name="Product ID", value=self.product_id.value, inline=False)
        embed.add_field(name="Artist Name / Handle", value=self.artist_name.value, inline=False)
        embed.add_field(name="Artist Email", value=self.artist_email.value, inline=False)
        embed.add_field(name="Sale Amount", value=self.sale_amount.value, inline=True)
        embed.add_field(name="Payment Method & Reference", value=self.payment_info.value, inline=True)
        embed.set_footer(text=f"Submitted by {interaction.user}")

        await thread.send(embed=embed)

        await interaction.followup.send(
            "Sale submitted successfully. Staff will verify the sale and payment, "
            "then complete the required fulfillment process.",
            ephemeral=True,
        )