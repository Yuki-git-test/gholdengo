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


def create_pokemon_lottery_embed(
    prize: str,
    host: discord.Member,
    max_tickets: int,
    ticket_price: int,
    ends_on: int,
    image_link: str,
    lottery_id: int,
):
    top_line = f"## Pokemon Lottery"
    if max_tickets == 0:
        max_tickets = "No Limit"

    guild = host.guild
    display_prize = get_display_name(prize, dex=True)
    display_duration = f"<t:{ends_on}:R>" if ends_on else "No time limit"
    display_cost = format_price_w_coin(ticket_price)
    embed_color = get_embed_color_by_rarity(prize)

    desc = (
        f"👤 **Host:** {host.mention}\n"
        f"🎁 **Prize:** {display_prize}\n"
        f"🎟️ **Tickets:** {max_tickets}\n"
        f"💵  **Cost per Ticket**: {display_cost}\n"
        f"⏰ **Ends:** {display_duration}\n"

    )
    buying_instructions = (
        f"To buy a ticket, use the command below in the lottery thread:\n"
        f";gift <@705447976658665552>  <amount> "
    )
    desc = top_line + "\n\n" + desc + "\n\n" + buying_instructions
    embed = discord.Embed(description=desc, color=embed_color)
    embed.add_field(name="Sold Tickets", value="None yet!", inline=False)
    embed.set_footer(text=f"Lottery ID: {lottery_id}", icon_url=guild.icon.url if guild.icon else None)
    if image_link:
        embed.set_image(url=image_link)
    return embed
