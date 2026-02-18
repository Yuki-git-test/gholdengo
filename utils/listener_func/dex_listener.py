# --------------------
#  Market embed parser utility
# --------------------
import re
from typing import Optional, Tuple

import discord

from utils.db.market_value_db import (
    fetch_image_link_cache,
    fetch_pokemon_exclusivity_cache,
    update_is_exclusive,
    upsert_image_link,
)
from utils.functions.pokemon_func import is_mon_exclusive
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

#enable_debug(f"{__name__}.dex_listener")


def extract_pokemon_name_and_dex(text):
    match = re.match(r"(.+?)\s*#(\d+)", text)
    if match:
        name = match.group(1).strip()
        dex = match.group(2).strip()
        return name, dex
    else:
        return text.strip(), None


async def dex_listener(bot, message: discord.Message):
    """Listens to dex command and updates the image link in the market value cache if it differs from the one in the command output."""
    embed = message.embeds[0] if message.embeds else None
    if not embed:
        return

    embed_title = embed.title if embed.title else ""
    embed_author_name = embed.author.name if embed.author else ""
    pokemon_name, dex_number = extract_pokemon_name_and_dex(embed_author_name)
    if not pokemon_name:
        debug_log(
            f"Could not extract pokemon name from embed title: '{embed_author_name}'"
        )
        return
    embed_image_url = embed.image.url if embed.image else None
    image_link_cache = fetch_image_link_cache(pokemon_name)
    existing_exclusive_status = fetch_pokemon_exclusivity_cache(pokemon_name)
    is_exclusive = is_mon_exclusive(pokemon_name)
    if existing_exclusive_status != is_exclusive and is_exclusive == False:
        new_exclusive = is_exclusive
        await update_is_exclusive(bot, pokemon_name, new_exclusive)
    else:
        new_exclusive = existing_exclusive_status
    if embed_image_url and image_link_cache != embed_image_url:
        await upsert_image_link(bot, pokemon_name, embed_image_url, new_exclusive)
        debug_log(
            f"Updated image link for {pokemon_name} to {embed_image_url} based on mh lookup command output."
        )
        pretty_log(
            "info",
            f"Updated image link for {pokemon_name} to {embed_image_url} based on mh lookup command output.",
        )
