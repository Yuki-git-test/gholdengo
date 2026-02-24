import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VN_ALLSTARS_TEXT_CHANNELS
from utils.db.lottery import fetch_lottery_info_by_lottery_id, is_lottery_active
from utils.db.lottery_entries import fetch_user_all_active_lottery_entries
from utils.functions.pokemon_func import format_price_w_coin, get_display_name
from utils.group_command_func.lottery.pokemon import if_testing_lottery
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


def calculate_winning_chance(user_entries: int, total_entries: int) -> float:
    if total_entries == 0:
        return "0%"
    else:
        chance = (user_entries / total_entries) * 100
        chance = round(chance, 2)
        chance = min(chance, 100.0)  # Cap at 100%
        # If decimal part is .00, show as whole number
        if chance.is_integer():
            chance_str = f"{int(chance)}%"
        else:
            chance_str = f"{chance:.2f}%"
        return chance_str


async def view_lottery_tickets_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
):
    """Lets a user view their lottery tickets across all active lotteries."""
    # Defer
    loader = await pretty_defer(
        interaction=interaction,
        content="Fetching your lottery tickets...",
        ephemeral=False,
    )
    # Fetch user's lottery entries across all lotteries
    user_id = interaction.user.id
    entries = await fetch_user_all_active_lottery_entries(bot, user_id)
    if not entries:
        await loader.error("You haven't bought any lottery tickets yet.")
        return

    channel, _ = if_testing_lottery(interaction.guild)
    LOTTERY_CHANNEL_ID = channel.id
    
    # Format the response message
    embed = discord.Embed(
        description="Here are your tickets for active lotteries:",
        color=discord.Color.gold(),
    )
    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )
    for entry in entries:
        lottery_id = entry["lottery_id"]
        lottery_info = await fetch_lottery_info_by_lottery_id(bot, lottery_id)
        lottery_type = lottery_info["lottery_type"]
        entries_count = entry["entries"]
        prize = lottery_info["prize"]
        total_tickets = lottery_info["total_tickets"]
        if lottery_type == "pokemon":
            prize_display_name = get_display_name(prize)
        elif lottery_type == "coin":
            # Ensure prize is numeric for formatting
            try:
                prize_display_name = format_price_w_coin(int(float(prize)))
            except (ValueError, TypeError):
                prize_display_name = str(prize)
        else:
            # Capitalize non-pokemon prizes
            prize_display_name = prize.title()
        ends_on = lottery_info["ends_on"]
        ends_on = int(ends_on)
        message_id = lottery_info["message_id"]
        chance = calculate_winning_chance(entries_count, total_tickets)
        chance_str = f"**Chance to win:** {chance}\n"
        lottery_link = f"https://discord.com/channels/{interaction.guild_id}/{LOTTERY_CHANNEL_ID}/{message_id}"
        title_str = f"🎫 Lottery ID: {lottery_id} - {prize_display_name}"

        ends_on_str = f"**Ends** <t:{ends_on}:R>\n" if ends_on > 0 else ""
        field_value_str = (
            f"> - [View Lottery]({lottery_link})\n"
            f"> - {ends_on_str}"
            f"> - **Tickets:** {entries_count}\n"
            f"> - {chance_str}"
        )
        embed.add_field(name=title_str, value=field_value_str, inline=False)

    await loader.success(content="", embed=embed)
