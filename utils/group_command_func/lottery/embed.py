import time

import discord
from discord.ext import commands

from utils.db.lottery import upsert_lottery
from utils.essentials.parsers import parse_compact_number
from utils.essentials.role_checks import *
from utils.functions.pokemon_func import (
    format_price_w_coin,
    get_display_name,
    get_embed_color_by_rarity,
)
from utils.logs.pretty_log import pretty_log
from utils.parsers.duration import parse_total_duration
from utils.visuals.get_pokemon_gif import get_pokemon_gif_from_cache
from utils.visuals.pretty_defer import pretty_defer
from utils.visuals.design_embed import design_embed
from Constants.lottery import Lotto_Extra_Entries

def format_lotto_extra_tickets(guild: discord.Guild) -> str:
    # Since Extra_Entries is now a dict mapping role_id to entry_bonus (int), ignore entry_group
    if not Lotto_Extra_Entries:
        return "No extra entries available."

    parts = []
    for role_id, entry_bonus in Lotto_Extra_Entries.items():
        role = guild.get_role(role_id)
        role_name = role.name if role else f"Role {role_id}"
        parts.append(f"{role_name} +{entry_bonus}")
    return ", ".join(parts)


def create_pokemon_lottery_embed(
    prize: str,
    host: discord.Member,
    max_tickets: int,
    ticket_price: int,
    ends_on: int,
    image_link: str,
):
    top_line = f"## Pokemon Lottery"
    if max_tickets == 0:
        max_tickets = "No Limit"

    guild = host.guild
    display_prize = get_display_name(prize, dex=True)
    display_duration = f"<t:{ends_on}:R>" if ends_on else "No time limit"
    display_cost = format_price_w_coin(ticket_price)
    embed_color = get_embed_color_by_rarity(prize)
    extra_ticket_display = format_lotto_extra_tickets(guild)

    desc = (
        f"👤 **Host:** {host.mention}\n"
        f"🎁 **Prize:** {display_prize}\n"
        f"🎟️ **Max Tickets:** {max_tickets}\n"
        f"💵  **Cost per Ticket**: {display_cost}\n"
        f"⏰ **Ends:** {display_duration}\n\n"
        f"💎 **Extra Tickets:** {extra_ticket_display}\n-# Bonus Tickets are added upon first purchase\n"
    )
    buying_instructions = (
        f"To buy a ticket, use the command below in the lottery thread:\n"
        f";gift <@705447976658665552>  <amount> "
    )
    desc = top_line + "\n\n" + desc + "\n" + buying_instructions
    embed = discord.Embed(description=desc, color=embed_color)
    embed.add_field(name="Sold Tickets", value="None yet!", inline=False)
    if image_link:
        embed.set_image(url=image_link)
    return embed
