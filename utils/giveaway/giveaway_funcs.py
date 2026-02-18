import discord

from Constants.giveaway import (
    BLACKLISTED_ROLES,
    DEFAULT_ALLOWED_DISPLAY,
    REQUIRED_ROLES,
    Extra_Entries,
    ALLOWED_JOIN_ROLES,
    format_roles_display,
)
from Constants.vn_allstars_constants import VN_ALLSTARS_ROLES
from utils.cache.global_variables import TESTING_GA
from utils.visuals.colors import get_random_ghouldengo_color
from utils.visuals.thumbnails import random_ga_thumbnail_url


def compute_total_entries(user: discord.Member):
    # Calculate total entries
    guild = user.guild
    total_entries = 1  # Base entry for joining
    contributing_roles = []
    for role_id, entry_bonus in Extra_Entries.items():
        role = guild.get_role(role_id)
        if role in user.roles:
            total_entries += entry_bonus
            if role:
                contributing_roles.append(role.name)
            else:
                contributing_roles.append(f"Role {role_id}")
    if total_entries > 1 and contributing_roles:
        bonus_text = f" (including {total_entries - 1} bonus entries from: {', '.join(contributing_roles)})"
    elif total_entries > 1:
        bonus_text = f" (including {total_entries - 1} bonus entries)"
    else:
        bonus_text = ""
    return total_entries, bonus_text

def format_extra_entries(guild: discord.Guild) -> str:
    # Since Extra_Entries is now a dict mapping role_id to entry_bonus (int), ignore entry_group
    if not Extra_Entries:
        return "No extra entries available."

    parts = []
    for role_id, entry_bonus in Extra_Entries.items():
        role = guild.get_role(role_id)
        role_name = role.name if role else f"Role {role_id}"
        parts.append(f"{role_name} +{entry_bonus}")
    return ", ".join(parts)


async def can_host_ga(user: discord.Member) -> bool:
    """Checks if the user has the required roles to host a giveaway."""
    user_roles = [role.id for role in user.roles]
    if not any(role in user_roles for role in REQUIRED_ROLES):
        required_roles_mentions = ", ".join(
            f"<@&{role_id}>" for role_id in REQUIRED_ROLES
        )
        error_msg = f"You do not have permission to use this command. Only members with the following roles can use it: {required_roles_mentions}"
        return False, error_msg
    return True, None


def build_ga_embed(
    host: discord.Member,
    giveaway_type: str,
    prize: str,
    ends_at: int,
    winners: int,
    image_link: str = None,
    message: str = None,
):
    """Builds the giveaway embed."""
    thumbnail_url = random_ga_thumbnail_url()
    ends_text = f"<t:{ends_at}:R>"
    allowed_roles_display = ""
    if giveaway_type == "clan":
        allowed_roles_display = format_roles_display(ALLOWED_JOIN_ROLES, host.guild)
    if giveaway_type == "server booster":
        allowed_roles_display = format_roles_display([VN_ALLSTARS_ROLES.server_booster], host.guild)

    extra_entries_display = format_extra_entries(host.guild)
    embed_color = get_random_ghouldengo_color()
    giveaway_role_mention = f"<@&{VN_ALLSTARS_ROLES.giveaways}>"

    blacklisted_roles_display = format_roles_display(BLACKLISTED_ROLES, host.guild)

    if TESTING_GA:
        giveaway_role_mention = f"<@& {VN_ALLSTARS_ROLES.giveaways}>"
    top_line = f"# 🎁 **{giveaway_type.upper()} GIVEAWAY** 🎁"
    desc_lines = [
        f"**Number of Winners:** {winners}",
        f"**Hosted by:** {host.mention}",
        f"**Prize:** {prize}",
        f"\n⏰ **Ends:** {ends_text}\n",
    ]

    if giveaway_type == "clan" or giveaway_type == "server booster":
        desc_lines.append(f"💙 **Allowed roles:** {allowed_roles_display}")
    desc_lines.append(f"🚫 **Blacklisted roles:** {blacklisted_roles_display}")
    desc_lines.append(f"\n✨ **Extra Entries:** {extra_entries_display}")
    desc = top_line + "\n" + "\n".join(desc_lines)
    embed = discord.Embed(description=desc, color=embed_color)
    if image_link:
        embed.set_image(url=image_link)
    embed.set_thumbnail(url=thumbnail_url)

    if message:
        content = f"{giveaway_role_mention}\n{message}"
    else:
        content = f"{giveaway_role_mention}"
    return embed, content
