import time

import discord
from discord.ext import commands

from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    YUKI_USER_ID,
)
from utils.cache.global_variables import TESTING_LOTTERY
from utils.db.lottery import update_message_and_thread, upsert_lottery
from utils.essentials.parsers import parse_compact_number
from utils.essentials.role_checks import *
from utils.functions.pokemon_func import is_mon_in_game
from utils.logs.pretty_log import pretty_log
from utils.parsers.duration import parse_lottery_duration
from utils.visuals.pretty_defer import pretty_defer
from Constants.aesthetic import Emojis
from .embed import create_coin_lottery_embed
from .pokemon import if_testing_lottery, validate_ticket_price

# ( {tickets x tickets price} x 75%)
TICKET_EMOJI = Emojis.lottery_ticket

async def coin_lottery_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    cost_per_ticket: str,
    base_pot: str = None,
    duration: str = None,
    max_tickets: str = None,
):
    # Defer
    loader = await pretty_defer(
        interaction=interaction, content="Setting up the lottery...", ephemeral=False
    )
    guild = interaction.guild
    # Check if staff
    if not is_staff_member(interaction.user):
        await loader.edit(content="You don't have permission to use this command.")
        return
    host = interaction.user

    #  Either duration or max tickets must be provided
    if not duration and not max_tickets:
        await loader.error(
            content="You must provide either a duration or a max tickets limit."
        )
        return

    # Parse cost per ticket
    parsed_cost = parse_compact_number(cost_per_ticket)
    if parsed_cost is None:
        await loader.error(
            content=f"'{cost_per_ticket}' is not a valid number for cost per ticket."
        )
        return
    if parsed_cost <= 0:
        await loader.error(content="Cost per ticket must be greater than zero.")
        return

    # Validate ticket price
    try:
        validate_ticket_price(parsed_cost)
    except ValueError as e:
        await loader.error(content=str(e))
        return

    # Parse base pot
    parsed_base_pot = 0
    if base_pot:
        parsed_base_pot = parse_compact_number(base_pot)
        if parsed_base_pot is None:
            await loader.error(
                content=f"'{base_pot}' is not a valid number for base pot."
            )
            return
        if parsed_base_pot < 0:
            await loader.error(content="Base pot cannot be negative.")
            return

    # Parse duration if provided
    ends_on = 0
    if duration:
        ends_on, error_msg = parse_lottery_duration(duration)
        if ends_on is None:
            await loader.error(content=error_msg)
            return
        if ends_on <= 0:
            await loader.error(content="Duration must be greater than zero.")
            return

    # Parse max tickets if provided
    max_tickets_int = 0
    if max_tickets:
        max_tickets_int = parse_compact_number(max_tickets)
        if max_tickets_int is None:
            await loader.error(
                content=f"'{max_tickets}' is not a valid number for max tickets."
            )
            return
        if max_tickets_int <= 0:
            await loader.error(content="Max tickets must be greater than zero.")
            return

    channel, mention = if_testing_lottery(guild)

    # Create embed
    try:
        embed, initial_prize = create_coin_lottery_embed(
            host=host,
            base_pot=parsed_base_pot,
            max_tickets=max_tickets_int,
            ticket_price=parsed_cost,
            ends_on=ends_on,
        )
    except Exception as e:
        pretty_log("error", f"Error creating lottery embed: {e}")
        await loader.error(
            content="An error occurred while creating the lottery embed. Please try again or contact Khy.",
        )

    # Upsert lottery in DB
    try:
        lottery_id = await upsert_lottery(
            bot=bot,
            prize=str(initial_prize),
            host_id=host.id,
            host_name=host.name,
            max_tickets=max_tickets_int,
            ticket_price=parsed_cost,
            base_pot=parsed_base_pot,
            ends_on=ends_on,
            ended=False,
            message_id=0,
            thread_id=0,
            total_tickets=0,
            lottery_type="coin",
            image_link=None,
            channel_id=channel.id,
        )
    except Exception as e:
        pretty_log("error", f"Error upserting lottery in DB: {e}")
        await loader.error(
            content="An error occurred while saving the lottery to the database. Please try again or contact Khy.",
        )
        return
    # Send embed
    try:
        sent_message = await channel.send(content=mention, embed=embed)
        thread = await sent_message.create_thread(
            name=f"🎟️ | Lottery ID: {lottery_id} - Coin Lottery"
        )
        await update_message_and_thread(bot, lottery_id, sent_message.id, thread.id)
        await loader.success(
            content=f"Lottery created successfully in {channel.mention}!"
        )
        # Edit embed to add lottery id in footer
        embed.set_footer(
            text=f"Lottery ID: {lottery_id}",
            icon_url=guild.icon.url if guild.icon else None,
        )
        await sent_message.edit(embed=embed)
    except Exception as e:
        pretty_log(tag="error", message=f"Error sending lottery message: {e}")
        await loader.error(
            content="An error occurred while sending the lottery message. Please try again or contact Khy."
        )
        return
