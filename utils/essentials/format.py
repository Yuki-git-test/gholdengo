from Constants.paldea_galar_dict import rarity_meta
from Constants.pokemon_dex import (
    common_mons,
    legendary_mons,
    superrare_mons,
    uncommon_mons,
)
from Constants.vn_allstars_constants import VN_ALLSTARS_EMOJIS


def format_commas(number: int) -> str:
    """Format a number with commas as thousand separators. If None, return 'None'."""
    if number is None:
        return "None"
    return f"{number:,}"


def format_comma_pokecoins(number: int) -> str:
    """Format a number with commas and add ' PokéCoins' suffix. If None, return 'None'."""
    if number is None:
        return "None"
    return f"{VN_ALLSTARS_EMOJIS.vna_pokecoin} {number:,}"


def format_pokemon_name(item_name: str, dex: str = None, context: str = None) -> str:
    """
    Format the item name for display.
    """

    MEGA_ITEMS = ["mega mewtwo y"]
    if "coin" in item_name.lower():
        return item_name  # No special formatting for currency items

    rarity = None
    lower_name = item_name.lower()
    if "shiny mega " in lower_name or "smega " in lower_name:
        rarity = "shiny mega"
        item_name = item_name.replace("Shiny Mega ", "").replace("SMega ", "")
    elif "shiny gigantamax" in lower_name:
        rarity = "shiny gigantamax"
        item_name = item_name.replace("Shiny Gigantamax ", "")
    elif "shiny " in lower_name:
        rarity = "shiny"
        item_name = item_name.replace("Shiny ", "")
    elif "golden mega " in lower_name or "gmega " in lower_name:
        rarity = "golden mega"
        item_name = item_name.replace("Golden Mega ", "").replace("GMega ", "")

    elif "golden " in lower_name:
        rarity = "golden"
        item_name = item_name.replace("Golden ", "")
    elif lower_name in legendary_mons:
        rarity = "legendary"
    elif lower_name in superrare_mons:
        rarity = "superrare"
    elif lower_name in uncommon_mons:
        rarity = "uncommon"
    elif lower_name in common_mons:
        rarity = "common"

    elif "gigantamax" in lower_name:
        rarity = "gmax"
        item_name = item_name.replace("Gigantamax ", "")

    elif lower_name in MEGA_ITEMS or "mega " in lower_name:
        rarity = "mega"
        item_name = item_name.replace("Mega ", "")

    rarity_emoji = rarity_meta.get(rarity, {}).get("emoji", "") if rarity else ""
    display_name = (
        f"{rarity_emoji} {item_name.title()}" if rarity_emoji else item_name.title()
    )
    has_dex = False
    if context and context.lower() == "no dex":
        has_dex = False
    elif dex and dex != "N/A":
        has_dex = True

    display_name = f"{display_name} #{dex}" if has_dex else display_name
    return display_name
