import discord

from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VN_ALLSTARS_ROLES

REQUIRED_ROLES = [
    VN_ALLSTARS_ROLES.staff,
    VN_ALLSTARS_ROLES.giveaway_host,
    VN_ALLSTARS_ROLES.seafoam,
]
ALLOWED_JOIN_ROLES = [VN_ALLSTARS_ROLES.vna_member]
BLACKLISTED_ROLES = [VN_ALLSTARS_ROLES.probation, VN_ALLSTARS_ROLES.double_probation, VN_ALLSTARS_ROLES.clan_break]


DEFAULT_ALLOWED_DISPLAY = ", ".join(f"<@&{rid}>" for rid in ALLOWED_JOIN_ROLES)
BLACKLISTED_DISPLAY = ", ".join(f"<@&{rid}>" for rid in BLACKLISTED_ROLES)

Extra_Entries = {
    VN_ALLSTARS_ROLES.amethyst_perks: 1,
    VN_ALLSTARS_ROLES.server_booster: 1,
    VN_ALLSTARS_ROLES.monthly_donator: 1,
    VN_ALLSTARS_ROLES.diamond_donator: 1,
    VN_ALLSTARS_ROLES.legendary_donator: 1,
    VN_ALLSTARS_ROLES.shiny_donator: 1,
}
GIVEAWAY_ROLES =[
    VN_ALLSTARS_ROLES.probation,
    VN_ALLSTARS_ROLES.double_probation,
    VN_ALLSTARS_ROLES.clan_break,
    VN_ALLSTARS_ROLES.vna_member,
    VN_ALLSTARS_ROLES.amethyst_perks,
    VN_ALLSTARS_ROLES.server_booster,
    VN_ALLSTARS_ROLES.monthly_donator,
    VN_ALLSTARS_ROLES.diamond_donator,
    VN_ALLSTARS_ROLES.legendary_donator,
    VN_ALLSTARS_ROLES.shiny_donator,
]
REG_GA_MIN_DURATION_SECONDS = 30 * 60

def format_roles_display(role_ids, guild: discord.Guild) -> str:

    if not role_ids:
        return "None"

    # Convert role IDs to role names
    role_names = []
    for role_id in role_ids:
        role = guild.get_role(role_id)
        if role:
            role_names.append(role.name)
        else:
            continue  # Skip if role not found
    return ", ".join(role_names) if role_names else "None"
