from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VN_ALLSTARS_ROLES

REQUIRED_ROLES = [
    VN_ALLSTARS_ROLES.staff,
    VN_ALLSTARS_ROLES.giveaway_host,
    VN_ALLSTARS_ROLES.seafoam,
]
ALLOWED_JOIN_ROLES = [VN_ALLSTARS_ROLES.vna_member]
BLACKLISTED_ROLES = [VN_ALLSTARS_ROLES.probation, VN_ALLSTARS_ROLES.double_probation]


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
