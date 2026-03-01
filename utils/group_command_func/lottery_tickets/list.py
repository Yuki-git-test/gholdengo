import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

from Constants.aesthetic import Emojis
from Constants.vn_allstars_constants import VN_ALLSTARS_TEXT_CHANNELS
from utils.db.lottery import fetch_lottery_info_by_lottery_id, is_lottery_active
from utils.db.lottery_entries import fetch_all_entries_for_a_lottery
from utils.functions.pokemon_func import format_price_w_coin, get_display_name
from utils.group_command_func.lottery.pokemon import if_testing_lottery
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer

TICKET_EMOJI = Emojis.lottery_ticket
from .view import calculate_winning_chance


class Lottery_Ticket_Paginator(View):
    def __init__(self, bot, user: discord.Member, entries, lottery_info, channel):
        super().__init__(timeout=120)  # 2 minute timeout
        self.bot = bot
        self.user = user
        self.entries = entries
        self.lottery_info = lottery_info
        self.channel = channel
        self.page = 0
        self.entries_per_page = 20
        self.max_page = (len(entries) - 1) // self.entries_per_page
        self.message = None  # Store message reference for later editing

        # If there's only one page, remove the buttons
        if self.max_page == 0:
            self.clear_items()

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with this button.", ephemeral=True
            )
            return
        self.page -= 1
        if self.page < 0:
            self.page = self.max_page
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with this button.", ephemeral=True
            )
            return
        self.page += 1
        if self.page > self.max_page:
            self.page = 0
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def get_embed(self):
        total_users = len(self.entries)
        start = self.page * self.entries_per_page
        end = start + self.entries_per_page
        page_entries = self.entries[start:end]
        guild = self.channel.guild
        lottery_type = self.lottery_info["lottery_type"]
        if lottery_type == "pokemon":
            prize_display = get_display_name(self.lottery_info["prize"], dex=False)
            base_pot_str = ""
        elif lottery_type == "coin":
            prize = int(self.lottery_info["prize"])
            prize_display = format_price_w_coin(prize)
            base_pot = self.lottery_info.get("base_pot", 0)
            base_pot = format_price_w_coin(base_pot) if base_pot > 0 else "No base pot"
            base_pot_str = f"> - **💰 Base Pot:** {base_pot}\n"
        else:
            prize_display = self.lottery_info["prize"].title()
        lottery_id = self.lottery_info["lottery_id"]
        title = f"Tickets for Lottery ID: {lottery_id}"
        ends_on = self.lottery_info["ends_on"]
        display_duration = f"<t:{ends_on}:R>" if ends_on else "No time limit"
        max_tickets = self.lottery_info["max_tickets"] or "No Limit"
        ticket_price = self.lottery_info["ticket_price"]
        formatted_ticket_price = format_price_w_coin(ticket_price)
        sold_tickets = self.lottery_info["total_tickets"]
        lottery_link = f"https://discord.com/channels/{guild.id}/{self.channel.id}/{self.lottery_info['message_id']}"
        desc = (
            f"> - [View Lottery]({lottery_link})\n"
            f"{base_pot_str}"
            f"> - 🎁 **Prize:** {prize_display}\n"
            f"> - {TICKET_EMOJI} **Max Tickets:** {max_tickets}\n"
            f"> - 💵  **Cost per Ticket**: {formatted_ticket_price}\n"
            f"> - ⏰ **Ends:** {display_duration}\n"
            f"> - 📊 **Total Tickets Sold:** {sold_tickets}\n\n"
        )

        embed = discord.Embed(title=title, color=discord.Color.gold(), description=desc)
        footer_text = f"Page {self.page + 1}/{self.max_page + 1} | Total Unique Participants: {total_users}"
        embed.set_footer(
            text=footer_text, icon_url=guild.icon.url if guild.icon else None
        )
        for idx, record in enumerate(page_entries, start=start + 1):
            user_id = record["user_id"]
            entries_count = record["entries"]
            user = guild.get_member(user_id)
            username = user.name or f"User ID {user_id}"
            amount_spent = entries_count * ticket_price
            formatted_amount_spent = format_price_w_coin(amount_spent)
            amount_spent_str = f"> - **Total Spent:** {formatted_amount_spent}\n"
            winning_chance = calculate_winning_chance(entries_count, sold_tickets)
            embed.add_field(
                name=f"{idx}. {username}",
                value=f"> - **Tickets:** {TICKET_EMOJI} {entries_count}\n{amount_spent_str}\n> - **Winning Chance:** {winning_chance}",
                inline=False,
            )
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception as e:
                pass  # Message was deleted, nothing to do


async def list_lottery_tickets_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    message_id: str,
):
    """Let's a staff member view the lottery tickets for a specific lottery by providing the lottery's message ID."""
    message_id = int(message_id)  # Ensure message_id is an integer
    pretty_log(
        message=f"Fetching lottery tickets for lottery with message ID {message_id}...",
        tag="info",
    )
    # Defer
    loader = await pretty_defer(
        interaction=interaction,
        content="Fetching lottery tickets...",
        ephemeral=False,
    )

    # Check if active
    lottery_info = await is_lottery_active(bot, message_id)
    if not lottery_info:
        await loader.error("No lottery found with that message ID.")
        return
    lottery_id = lottery_info["lottery_id"]
    channel, _ = if_testing_lottery(interaction.guild)

    entries = await fetch_all_entries_for_a_lottery(bot, lottery_id)
    if not entries:
        await loader.error("No tickets have been bought for this lottery yet.")
        return

    entries = await fetch_all_entries_for_a_lottery(bot, lottery_id)
    if not entries:
        await loader.error("No tickets have been bought for this lottery yet.")
        return

    sorted_entries = sorted(entries, key=lambda x: x["entries"], reverse=True)
    pretty_log(message=f"DEBUG: Entries for lottery: {sorted_entries}", tag="debug")
    try:
        paginator = Lottery_Ticket_Paginator(
            bot=bot,
            user=interaction.user,
            entries=sorted_entries,
            lottery_info=lottery_info,
            channel=channel,
        )
        embed = await paginator.get_embed()
        sent_msg = await loader.success(
            content="",
            embed=embed,
            view=paginator,
        )
        paginator.message = sent_msg
    except Exception as e:
        await loader.error(
            content="An error occurred while fetching the lottery tickets."
        )
        pretty_log(
            message=f"❌ Error in list_lottery_tickets_func: {e}",
            tag="error",
            include_trace=True,
        )
