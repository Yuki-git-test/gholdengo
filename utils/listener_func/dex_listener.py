# --------------------
#  Market embed parser utility
# --------------------
import re
from typing import Optional, Tuple

import discord

from utils.db.market_value_db import (
    fetch_dex_number_cache,
    fetch_image_link_cache,
    fetch_pokemon_exclusivity_cache,
    fetch_rarity_cache,
    update_dex_number,
    update_is_exclusive,
    update_rarity,
    upsert_image_link,
)
from utils.functions.pokemon_func import is_mon_exclusive
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

# enable_debug(f"{__name__}.dex_listener")

emoji_map = {
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "superrare": "superrare",
    "legendary": "legendary",
    "shiny": "shiny",
    "golden": "golden",
    "shinymega": "shiny mega",
    "shinygigantamax": "shiny gigantamax",
    "mega": "mega",
    "gigantamax": "gigantamax",
    "goldenmega": "golden mega",
    "goldengigantamax": "golden gigantamax",
}


def extract_pokemon_name_and_dex(text):
    match = re.match(r"(.+?)\s*#(\d+)", text)
    if match:
        name = match.group(1).strip()
        dex = match.group(2).strip()
        return name, dex
    else:
        return text.strip(), None


def extract_rarity_from_embed(embed) -> str:
    """
    Extracts the rarity text or emoji name from the 'Rarity' field in a Discord embed object.
    Returns the mapped rarity as a string (e.g., 'shiny gigantamax').
    """
    debug_log("Starting rarity extraction from embed.")
    fields = []
    # Try to get fields from embed object (discord.py Embed or dict)
    if hasattr(embed, "fields"):
        fields = embed.fields
        debug_log(f"Embed fields attribute found: {fields}")
    elif isinstance(embed, dict) and "fields" in embed:
        fields = embed["fields"]
        debug_log(f"Embed fields key found: {fields}")
    else:
        debug_log(f"Embed has no fields attribute or key. Embed: {embed}")
    for idx, field in enumerate(fields):
        debug_log(f"Checking field {idx}: {field}")
        name = (
            field.get("name")
            if isinstance(field, dict)
            else getattr(field, "name", None)
        )
        value = (
            field.get("value")
            if isinstance(field, dict)
            else getattr(field, "value", None)
        )
        debug_log(f"Field name: {name}, value: {value}")
        if name and name.lower() == "rarity":
            debug_log(f"Found 'Rarity' field with value: {value}")
            match = re.search(r"<:([a-zA-Z0-9_]+):[0-9]+>", value)
            if match:
                emoji_name = match.group(1)
                debug_log(f"Extracted emoji name: {emoji_name}")
                mapped_rarity = emoji_map.get(emoji_name.lower(), emoji_name)
                debug_log(f"Mapped rarity: {mapped_rarity}")
                return mapped_rarity
            debug_log(f"Returning plain rarity value: {value.strip()}")
            return value.strip()
    debug_log("'Rarity' field not found in embed.")
    return ""


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
    old_dex_number = fetch_dex_number_cache(pokemon_name)
    if dex_number and str(old_dex_number) != str(dex_number):
        dex_number = int(dex_number)
        await update_dex_number(bot, pokemon_name, dex_number)
        debug_log(
            f"Updated dex number for {pokemon_name} to {dex_number} based on mh lookup command output."
        )
        pretty_log(
            "info",
            f"Updated dex number for {pokemon_name} to {dex_number} based on mh lookup command output.",
        )
    old_rarity = fetch_rarity_cache(pokemon_name)
    rarity = extract_rarity_from_embed(embed)

    if rarity and old_rarity != rarity:
        await update_rarity(bot, pokemon_name, rarity)
        debug_log(f"Updated rarity for {pokemon_name} to {rarity}.")
        pretty_log(
            "info",
            f"Updated rarity for {pokemon_name} to {rarity}.",
        )
