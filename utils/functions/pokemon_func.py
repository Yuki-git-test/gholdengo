from Constants.pokemon_dex import *
from utils.db.market_value_db import (
    fetch_market_value_cache,
    is_pokemon_exclusive_cache,
)
from utils.logs.debug_log import debug_log, enable_debug
from Constants.paldea_galar_dict import get_dex_number_by_name, rarity_meta
from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    YUKI_USER_ID,
)

IN_GAME_MONS_LIST = (
    list(common_mons.keys())
    + list(uncommon_mons.keys())
    + list(rare_mons.keys())
    + list(superrare_mons.keys())
    + list(legendary_mons.keys())
    + list(mega_mons.keys())
    + list(gigantamax_mons.keys())
    + list(shiny_mons.keys())
    + list(shiny_mega_mons.keys())
    + list(shiny_gigantamax_mons.keys())
    + list(golden_mons.keys())
    + list(exclusive_mons.keys())
)

exclusive_mons_list = list(exclusive_mons.keys())

def get_embed_color_by_rarity(pokemon_name: str) -> int:
    rarity = get_rarity(pokemon_name)
    if rarity and rarity in rarity_meta:
        return rarity_meta[rarity]["color"]
    else:
        return 0xFFFFFF  # Default to white if rarity is unknown

def format_price_w_coin(n: int) -> str:
    """Format PokeCoin price with commas (no K/M shorthand)."""
    pokecoin = VN_ALLSTARS_EMOJIS.vna_pokecoin
    return f"{pokecoin} {n:,}"


def get_display_name(pokemon_name: str, dex: bool = False) -> str:
    """Returns the display name of a Pokémon, optionally including the dex number."""

    rarity = get_rarity(pokemon_name)
    rarity_emoji = rarity_meta.get(rarity, {}).get("emoji", "") if rarity else ""
    display_name = f"{rarity_emoji} {pokemon_name}".strip()

    if dex:
        dex_number = get_dex_number_by_name(pokemon_name)
        if dex_number:
            display_name = f"{display_name} #{dex_number}"
    return display_name.strip()


# enable_debug(f"{__name__}.is_mon_exclusive")
def is_mon_exclusive(pokemon: str) -> bool:
    """
    Checks if a given Pokémon is exclusive based on the exclusive_mons list or the market value cache.
    """
    debug_log(f"Checking exclusivity for: {pokemon}")
    name = pokemon.lower()
    if any(name == mon.lower() for mon in exclusive_mons_list):
        debug_log(f"{pokemon} is exclusive based on the exclusive_mons list.")
        return True
    # Check cache for exclusivity, if it's exclusive then it's not auctionable
    pokemon = format_names_for_market_value_lookup(pokemon)
    if is_pokemon_exclusive_cache(pokemon):
        debug_log(f"{pokemon} is exclusive based on the market value cache.")
        return True
    else:
        debug_log(f"{pokemon} is not exclusive based on the market value cache.")
        return False


def get_rarity(pokemon: str):
    """Determines the rarity of a given Pokemon based on the name"""

    name = pokemon.lower()
    if "golden" in name:
        return "golden"
    elif "shiny" in name and "gigantamax" in name:
        return "sgmax"
    elif "shiny" in name and "mega" in name:
        return "smega"
    elif "shiny" in name:
        return "shiny"
    elif "gigantamax" in name:
        return "gmax"
    elif "mega" in name and not "yanmega" in name and not "meganium" in name:
        return "mega"

    # Fallback to the list (case-insensitive)
    elif name in (mon.lower() for mon in legendary_mons):
        return "legendary"
    elif name in (mon.lower() for mon in superrare_mons):
        return "super rare"
    elif name in (mon.lower() for mon in rare_mons):
        return "rare"
    elif name in (mon.lower() for mon in uncommon_mons):
        return "uncommon"
    elif name in (mon.lower() for mon in common_mons):
        return "common"
    else:
        return None


def format_names_for_market_value_lookup(pokemon_name: str):
    """
    Format Pokémon name for market value lookup"""
    # Special log for names containing '-o'
    if "-o" in pokemon_name:
        debug_log(f"SPECIAL: '-o' detected in name: {pokemon_name!r}")
    # Special log for 'type null'
    if pokemon_name.lower().strip() == "type null":
        debug_log(f"SPECIAL: 'type null' detected: {pokemon_name!r}")
    pokemon_name = pokemon_name.lower().strip()
    if pokemon_name.startswith("sgmax "):
        # shiny gigantamax-<name>
        base = pokemon_name[6:].strip()
        result = f"shiny gigantamax-{base}"
        # debug_log(f"sgmax result: {result}")
        return result
    elif pokemon_name.startswith("gmax "):
        # gigantamax-<name>
        base = pokemon_name[5:].strip()
        result = f"gigantamax-{base}"
        # debug_log(f"gmax result: {result}")
        return result
    elif "smega" in pokemon_name:
        result = pokemon_name.replace("smega", "shiny mega").replace("-", " ")
        # debug_log(f"smega result: {result}")
        return result
    elif "mega" in pokemon_name:
        result = pokemon_name.replace("-", " ")
        # debug_log(f"mega result: {result}")
        return result
    else:
        # debug_log(f"default result: {pokemon_name}")
        return pokemon_name


def is_mon_in_game(pokemon_name: str) -> bool:
    """Check if a Pokémon is in the game."""
    name_lower = pokemon_name.lower()
    if name_lower in IN_GAME_MONS_LIST:
        return True
    # Fallback to check if the formatted name is in the market value cache
    pokemon_name_formatted = format_names_for_market_value_lookup(pokemon_name)
    market_value = fetch_market_value_cache(pokemon_name_formatted)
    if market_value is not None:
        return True
    return False
