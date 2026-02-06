from .vn_allstars_constants import VN_ALLSTARS_ROLES

MONTHLY_DONATION_VALUE = 10_000_000  # 10 million
DIAMOND_DONATION_VALUE = 50_000_000  # 50 million
LEGENDARY_DONATION_VALUE = 100_000_000  # 100 million
SHINY_DONATION_VALUE = 250_000_000  # 250 million

DONATION_MILESTONE_MAP = {
    "monthly_donator": {
        "role_id": VN_ALLSTARS_ROLES.monthly_donator,
        "threshold": MONTHLY_DONATION_VALUE,
    },
    "diamond_donator": {
        "role_id": VN_ALLSTARS_ROLES.diamond_donator,
        "threshold": DIAMOND_DONATION_VALUE,
    },
    "legendary_donator": {
        "role_id": VN_ALLSTARS_ROLES.legendary_donator,
        "threshold": LEGENDARY_DONATION_VALUE,
    },
    "shiny_donator": {
        "role_id": VN_ALLSTARS_ROLES.shiny_donator,
        "threshold": SHINY_DONATION_VALUE,
    },
}
