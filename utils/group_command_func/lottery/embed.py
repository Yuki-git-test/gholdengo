import time

import discord
from discord.ext import commands

from Constants.lottery import Lotto_Extra_Entries
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
from utils.visuals.design_embed import design_embed
from utils.visuals.get_pokemon_gif import get_pokemon_gif
from utils.visuals.pretty_defer import pretty_defer


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
    embed_color = get_embed_color_by_rarity(
        prize
    )  # You can choose a color based on the prize rarity if you have that info
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


def create_coin_lottery_embed(
    host: discord.Member,
    base_pot: int,
    max_tickets: int,
    ticket_price: int,
    ends_on: int,
):
    top_line = f"## Coin Lottery"
    if max_tickets == 0:
        max_tickets = "No Limit"
    prize_formula = f"[(tickets x tickets price) x 75%]"
    guild = host.guild
    display_duration = f"<t:{ends_on}:R>" if ends_on else "No time limit"
    display_cost = format_price_w_coin(ticket_price)
    base_pot_str = "**💰 No Base Pot**\n"
    initial_prize = 0
    if base_pot > 0:
        base_pot_display = f"{format_price_w_coin(base_pot)}"
        base_pot_str = f"**💰 Base Pot:** {base_pot_display}\n"
        prize_formula = f"{base_pot_display} + [(tickets x tickets price) x 75%]"
        initial_prize = int(base_pot)  # Base pot contributes to the initial prize pool
    embed_color = discord.Color.gold()
    extra_ticket_display = format_lotto_extra_tickets(guild)

    desc = (
        f"👤 **Host:** {host.mention}\n"
        f"{base_pot_str}"
        f"🎁 **Pot Formula:** {prize_formula}\n"
        f"🎟️ **Max Tickets:** {max_tickets}\n"
        f"💵  **Cost per Ticket**: {display_cost}\n"
        f"⏰ **Ends:** {display_duration}\n\n"
        f"💎 **Extra Tickets:** {extra_ticket_display}\n-# Bonus Tickets are added upon first purchase\n"
        f"25% of this lotto will go to Vna bank and the rest will go to winner.\n"
    )
    buying_instructions = (
        f"To buy a ticket, use the command below in the lottery thread:\n"
        f";gift <@705447976658665552>  <amount> "
    )

    desc = top_line + "\n\n" + desc + "\n" + buying_instructions
    embed = discord.Embed(description=desc, color=embed_color)
    embed.add_field(
        name="Current Pot", value=format_price_w_coin(initial_prize), inline=False
    )
    embed.add_field(name="Sold Tickets", value="None yet!", inline=False)

    return embed, initial_prize
