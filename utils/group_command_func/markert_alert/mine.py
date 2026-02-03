import discord
from discord.ui import Button, View

from Constants.aesthetic import *
from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VN_ALLSTARS_EMOJIS
from utils.db.market_alert_user import fetch_market_alert_user
from utils.logs.pretty_log import pretty_log
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer


class Market_Alerts_Paginator(View):
    def __init__(
        self, bot, user, alerts, alerts_used, max_alerts, per_page=5, timeout=180
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.user = user
        self.alerts = alerts
        self.alerts_used = alerts_used
        self.max_alerts = max_alerts
        self.per_page = per_page
        self.page = 0
        self.max_page = (len(alerts) - 1) // per_page
        self.message: discord.Message = None  # store the sent message

        # If there's only one page, remove the buttons
        if self.max_page == 0:
            self.clear_items()

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with this paginator.", ephemeral=True
            )
            return
        self.page -= 1
        if self.page < 0:
            self.page = self.max_page
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with this paginator.", ephemeral=True
            )
            return
        self.page += 1
        if self.page > self.max_page:
            self.page = 0
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    async def get_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        page_alerts = self.alerts[start:end]

        embed = discord.Embed(
            title=f"🛍️ Market Alerts",
            description=f"**Alerts Used:** {self.alerts_used}/{self.max_alerts}",
            color=DEFAULT_EMBED_COLOR,
        )
        for idx, alert in enumerate(page_alerts, start=1 + self.page * self.per_page):
            role_str = (
                f"<@&{alert['role_id']}>" if alert["role_id"] else "No role assigned"
            )

            embed.add_field(
                name=f"{idx}. {alert['pokemon'].title()} #{alert['dex']}",
                value=(
                    f"> - **Max Price:** {VN_ALLSTARS_EMOJIS.vna_pokecoin} {alert['max_price']}\n"
                    f"> - **Channel:** <#{alert['channel_id']}>\n"
                    f"> - **Role:** {role_str}\n"
                ),
                inline=False,
            )
        footer_text = f"Page {self.page + 1} of {self.max_page + 1}"
        embed = design_embed(
            embed=embed,
            user=self.user,
            footer_text=footer_text,
        )
        return embed

    async def on_timeout(self):
        """Disable all buttons when paginator times out."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception as e:
                pretty_log("error", f"Failed to disable paginator buttons: {e}")


async def mine_market_alert_func(bot, interaction: discord.Interaction):
    """
    Fetches and displays all market alerts for the invoking user.
    """

    user = interaction.user
    user_id = user.id
    user_name = user.name
    guild = interaction.guild

    # Initialize loader
    loader = await pretty_defer(
        interaction=interaction,
        content="Fetching your market alerts...",
        ephemeral=False,
    )

    # Fetch user's market alerts from cache
    from utils.cache.market_alert_cache import fetch_user_alerts_from_cache

    user_alerts = fetch_user_alerts_from_cache(user_id)
    if not user_alerts:
        await loader.error("You have no market alerts set up.")
        return

    # Sort alerts by dex
    alerts = sorted(
        user_alerts,
        key=lambda alert: (
            int(str(alert["dex"]).lstrip("0"))
            if str(alert["dex"]).isdigit()
            else float("inf")
        ),
    )
    # Fetch user's alert usage info
    alert_user = await fetch_market_alert_user(bot, user_id)
    alerts_used = alert_user["alerts_used"]
    max_alerts = alert_user["max_alerts"]

    # Create paginator
    paginator = Market_Alerts_Paginator(
        bot=bot,
        user=user,
        alerts=alerts,
        alerts_used=alerts_used,
        max_alerts=max_alerts,
        per_page=5,
    )
    embed = await paginator.get_embed()
    sent = await loader.success(embed=embed, view=paginator, content="")
    paginator.message = sent  # store the sent message for timeout handling
