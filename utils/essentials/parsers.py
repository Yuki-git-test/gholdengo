# ─────────────────────────────────────────────
# Helper: normalize Mega Pokemon name for database/display
# ─────────────────────────────────────────────
import re
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from Constants.vn_allstars_constants import VN_ALLSTARS_EMOJIS
from Constants.weakness_chart import weakness_chart
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

Shiny_Emoji = VN_ALLSTARS_EMOJIS.vna_shiny
Golden_Emoji = VN_ALLSTARS_EMOJIS.vna_golden
PREFIX_EMOJI_MAP = {
    "shiny ": Shiny_Emoji,
    "golden ": Golden_Emoji,
}

FORM_BASE_DEX_OFFSET = 7001

enable_debug(f"{__name__}.parse_special_mega_input")


# ─────────────────────────────────────────────
# Helper: Resolve Pokemon Name and Dex
# ─────────────────────────────────────────────
def resolve_pokemon_input(pokemon_input: str):
    """
    Converts any user input (name or dex) into a normalized Pokemon name and Dex number.
    Handles:
    - Numeric Dex input (normal, shiny, golden, special forms)
    - Name input (including shiny/golden prefixes, Mega forms)
    Returns: (display_name, dex_number)
    """
    pokemon_input = pokemon_input.strip().lower()

    # ── Numeric Dex input ──
    if pokemon_input.isdigit():
        dex_int = int(pokemon_input)

        first_digit = pokemon_input[0]
        prefix = ""
        if first_digit == "9" and len(pokemon_input) > 3:
            base_dex = int(pokemon_input[1:])
            prefix = "Golden "
        elif first_digit == "1" and len(pokemon_input) > 3:
            base_dex = int(pokemon_input[1:])
            prefix = "Shiny "
        else:
            base_dex = int(pokemon_input)

        # Lookup in weakness chart
        for name, data in weakness_chart.items():
            chart_dex = int(str(data.get("dex")).lstrip("0"))
            if chart_dex == base_dex:
                display_name = prefix + format_mega_pokemon_name(name)

                return display_name, dex_int

        raise ValueError(f"No Pokemon found with Dex #{dex_int}")

    # ── Name input ──
    else:
        prefix = ""
        if pokemon_input.startswith("shiny "):
            prefix = "Shiny "
            base_name = pokemon_input[6:]
        elif pokemon_input.startswith("golden "):
            prefix = "Golden "
            base_name = pokemon_input[7:]
        else:
            base_name = normalize_mega_input(pokemon_input)

        chart_data = weakness_chart.get(base_name)
        if not chart_data or "dex" not in chart_data:

            raise ValueError(f"No Pokemon found with name {base_name}")

        display_name = prefix + format_mega_pokemon_name(base_name)

        #
        # Calculate Dex with offsets, but skip for 7xxx forms
        chart_dex_int = int(chart_data["dex"])
        if chart_dex_int >= 7000:
            dex_number = chart_dex_int  # already a form, skip Shiny/Golden offsets

        else:
            if prefix == "Shiny ":
                dex_number = chart_dex_int + 1000
            elif prefix == "Golden ":
                dex_number = chart_dex_int + 9000
            else:
                dex_number = chart_dex_int

        return display_name, dex_number


def normalize_mega_input(name: str) -> str:
    """Converts user input for Mega Pokemon into chart-friendly format."""
    name = name.strip().lower()
    if name.startswith("mega"):
        result = name.replace(" ", "-")  # replace all spaces
        return result
    return name


def old_parse_special_mega_input(name: str) -> int:
    """Parses input for Pokemon, handling Shiny/Golden prefixes and Mega forms."""

    name = name.strip().lower()
    prefix = None
    pretty_log("debug", f"Parsing special mega input for '{name}'", label="PARSE MEGA")
    # Detect shiny/golden prefix
    for p in ["shiny", "golden"]:
        if name.startswith(p):
            prefix = p
            name = name[len(p) :].strip()
            pretty_log(
                "debug",
                f"Detected prefix: {prefix}, remaining name: '{name}'",
                label="PARSE MEGA",
            )
            break

    # Normalize mega forms
    if name.startswith("mega"):
        name = name.replace(" ", "-")
        pretty_log("debug", f"Normalized mega name: '{name}'", label="PARSE MEGA")

    # Try prefixed mega name first
    lookup_name = f"{prefix} {name}" if prefix else name
    lookup_name = lookup_name.strip()
    pretty_log("debug", f"Trying lookup_name: '{lookup_name}'", label="PARSE MEGA")
    if lookup_name in weakness_chart:
        dex_number = int(weakness_chart[lookup_name]["dex"])
        pretty_log(
            "debug", f"Found dex for '{lookup_name}': {dex_number}", label="PARSE MEGA"
        )
    elif name in weakness_chart:
        dex_number = int(weakness_chart[name]["dex"])
        pretty_log("debug", f"Found dex for '{name}': {dex_number}", label="PARSE MEGA")
    else:
        pretty_log(
            "error",
            f"No entry found for '{lookup_name}' or '{name}' in weakness_chart",
            label="PARSE MEGA",
        )
        raise ValueError(
            f"No entry found for {lookup_name} or {name} in weakness_chart"
        )

    # Apply shiny/golden offset only if not already a prefixed mega
    if prefix == "shiny" and lookup_name == name:
        final_dex = dex_number + 1
        pretty_log("debug", f"Applied shiny offset: {final_dex}", label="PARSE MEGA")
    elif prefix == "golden" and lookup_name == name:
        final_dex = dex_number + 2
        pretty_log("debug", f"Applied golden offset: {final_dex}", label="PARSE MEGA")
    else:
        final_dex = dex_number
        pretty_log(
            "debug", f"No offset applied, final dex: {final_dex}", label="PARSE MEGA"
        )

    return final_dex


def parse_special_mega_input(name: str) -> int:
    """Parses input for Pokemon, handling Shiny/Golden prefixes and Mega forms."""

    name = name.strip().lower()
    prefix = None
    pretty_log("debug", f"Parsing special mega input for '{name}'", label="PARSE MEGA")
    # Detect shiny/golden prefix
    for p in ["shiny", "golden"]:
        if name.startswith(p):
            prefix = p
            name = name[len(p) :].strip()
            break

    # Normalize mega forms
    if name.startswith("mega"):
        name = name.replace(" ", "-")
    debug_log(f"Normalized mega name: '{name}'")
    # Try prefixed mega name first
    lookup_name = f"{prefix} {name}" if prefix else name
    lookup_name = lookup_name.strip()
    debug_log(f"Trying lookup_name: '{lookup_name}'")

    if lookup_name in weakness_chart:
        debug_log(f"{lookup_name}' found in weakness_chart")
        dex_number = int(weakness_chart[lookup_name]["dex"])
        debug_log(f"Found dex for '{lookup_name}': {dex_number}")
    elif name in weakness_chart:
        debug_log(f"'{name}' found in weakness_chart")
        dex_number = int(weakness_chart[name]["dex"])
        debug_log(f"Found dex for '{name}': {dex_number}")
    else:
        raise ValueError(
            f"No entry found for {lookup_name} or {name} in weakness_chart"
        )

    # Apply shiny/golden offset only if not already a prefixed mega
    if prefix == "shiny" and lookup_name == name:
        final_dex = dex_number + 1
        debug_log(f"Applied shiny offset: {final_dex}")
    elif prefix == "golden" and lookup_name == name:
        final_dex = dex_number + 2
        debug_log(f"Applied golden offset: {final_dex}")
    else:
        final_dex = dex_number

    return final_dex


def format_mega_pokemon_name(name: str) -> str:
    """Replace hyphen with space and title-case Mega forms."""
    if name.lower().startswith("mega-") or name.lower().startswith("mega "):
        result = name.replace("-", " ").title()
        return result

    return name


def parse_form_pokemon(dex_int: int, weakness_chart: dict):
    """Returns display-friendly Pokemon name and dex using only weakness_chart."""

    # Search for an entry in weakness_chart with matching dex
    for name, data in weakness_chart.items():
        try:
            entry_dex = int(data.get("dex"))
        except (TypeError, ValueError):
            continue

        if entry_dex == dex_int:
            # Determine variant from name prefix
            if name.lower().startswith("shiny "):
                variant_type = "shiny"
                display_name = name[6:].title()  # Remove 'shiny ' prefix
            elif name.lower().startswith("golden "):
                variant_type = "golden"
                display_name = name[7:].title()  # Remove 'golden ' prefix
            else:
                variant_type = "regular"
                display_name = name.title()

            return display_name, entry_dex, variant_type

    # If not found
    return None, None, None


# 💜────────────────────────────────────────────
#         [🤍 HELPER] Parse Compact Number
# 💜────────────────────────────────────────────
def parse_compact_number(raw_number: str) -> Optional[int]:
    """
    Converts human-friendly numbers (e.g. '1k', '1.1m', '1.2b', '1 000k') to int.
    Returns None if invalid.
    """

    if not isinstance(raw_number, str):
        return None

    # Normalize input
    raw_number = raw_number.strip().lower().replace(",", "").replace(" ", "")

    # Accept formats like 1.1k, 1000, 1.54m, 1.100k
    pattern = r"^(\d+(?:\.\d+)?)([kmb]?)$"
    match = re.fullmatch(pattern, raw_number)
    if not match:
        return None

    num_str, suffix = match.groups()

    try:
        number = float(num_str)
    except ValueError:
        return None

    # Apply suffix multiplier
    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    elif suffix == "b":
        number *= 1_000_000_000

    # Safety range (avoid nonsense like 1e50)
    if number <= 0 or number > 10_000_000_000:
        return None

    return int(number)


# 💜────────────────────────────────────────────
#       [🤍 HELPER] Prefix → Emoji Parser
# 💜────────────────────────────────────────────
def parse_prefix(input_str: str) -> str:
    """
    Detects prefixes like 'shiny ' or 'golden ' and replaces them
    with their corresponding emoji prefix.

    Examples:
        "Shiny Cottonee" → "<:shiny:123...> Cottonee"
        "golden Eevee"   → "<:golden11:123...> Eevee"
        "Eevee"          → "Eevee"
    """
    if not isinstance(input_str, str):
        return input_str

    stripped = input_str.strip()
    lower = stripped.lower()

    for prefix, emoji in PREFIX_EMOJI_MAP.items():
        if lower.startswith(prefix):
            # Remove the text prefix (e.g. "shiny ")
            without_prefix = stripped[len(prefix) :].strip()
            return f"{emoji} {without_prefix.title()}"

    # If no recognized prefix, return as-is
    return stripped.title()
