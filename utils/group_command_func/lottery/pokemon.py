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
from utils.visuals.get_pokemon_gif import get_pokemon_gif_from_cache
from utils.visuals.pretty_defer import pretty_defer

from .embed import create_pokemon_lottery_embed


def if_testing_lottery(guild: discord.Guild):
    test_channel_id = VN_ALLSTARS_TEXT_CHANNELS.khys_chamber
    real_channel_id = VN_ALLSTARS_TEXT_CHANNELS.lottery
    mention = f"<@&{VN_ALLSTARS_ROLES.lottery}>"
    if TESTING_LOTTERY:
        channel_id = test_channel_id
        mention = ""
    else:
        channel_id = real_channel_id
    channel = guild.get_channel(channel_id)
    return channel, mention


def validate_ticket_price(ticket_price: int):
    """
    Raises ValueError if ticket_price is not a 'nice' number.
    Only allows multiples of 100.
    """
    if ticket_price <= 0:
        raise ValueError("Ticket price must be positive.")
    if ticket_price % 100 != 0:
        raise ValueError("Ticket price should be a round number (multiple of 100).")


async def pokemon_lottery_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    pokemon_name: str,
    cost_per_ticket: str,
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

    # Check if valid mon
    if not is_mon_in_game(pokemon_name):
        await loader.error(
            content=f"'{pokemon_name}' is not a valid Pokémon name or not in game yet."
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

    # Get Pokémon GIF
    gif_url = get_pokemon_gif_from_cache(pokemon_name)
    if not gif_url:
        await loader.error(
            content=f"Could not find a GIF for '{pokemon_name}'. Please check the name and try again or contact Khy."
        )
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
        embed = create_pokemon_lottery_embed(
            prize=pokemon_name,
            host=host,
            max_tickets=max_tickets_int,
            ticket_price=parsed_cost,
            ends_on=ends_on,
            image_link=gif_url,
        )
    except Exception as e:
        pretty_log(tag="error", message=f"Error creating embed: {e}")
        await loader.error(
            content="An error occurred while creating the lottery embed. Please try again or contact Khy."
        )
        return

    # Upsert lottery in DB
    try:
        lottery_id = await upsert_lottery(
            bot=bot,
            prize=pokemon_name,
            host_id=host.id,
            host_name=host.name,
            max_tickets=max_tickets_int,
            ticket_price=parsed_cost,
            base_pot=0,
            ends_on=ends_on,
            ended=False,
            message_id=0,
            thread_id=0,
            image_link=gif_url,
            total_tickets=0,
            channel_id=channel.id,
        )
    except Exception as e:
        pretty_log(tag="error", message=f"Error upserting lottery: {e}")
        await loader.error(
            content="An error occurred while setting up the lottery. Please try again or contact Khy."
        )
        return

    # Send embed
    try:
        sent_message = await channel.send(content=mention, embed=embed)
        thread = await sent_message.create_thread(
            name=f"🎟️ | Lottery ID: {lottery_id} - {pokemon_name}"
        )
        await update_message_and_thread(bot, lottery_id, sent_message.id, thread.id)
        await loader.success(
            content=f"Lottery created successfully in {channel.mention}!"
        )
        # Edit embed to add lottery id in footer
        embed.set_footer(
            text=f"Lottery ID: {lottery_id}", icon_url=guild.icon.url if guild.icon else None
        )
        await sent_message.edit(embed=embed)
    except Exception as e:
        pretty_log(tag="error", message=f"Error sending lottery message: {e}")
        await loader.error(
            content="An error occurred while sending the lottery message. Please try again or contact Khy."
        )
        return
