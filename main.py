# main.py
import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands, tasks

from Constants.variables import DATA_DIR, DEFAULT_GUILD_ID
from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.cache.cache_list import clear_processed_messages_cache
from utils.cache.central_cache_loader import load_all_cache
from utils.db.get_pg_pool import get_pg_pool
from utils.logs.pretty_log import pretty_log, set_ghouldengo_bot

# ---- Intents / Bot ----
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix=";", intents=intents)
set_ghouldengo_bot(bot)


# 🟣────────────────────────────────────────────
#         ⚡ Hourly Cache Refresh Task ⚡
# 🟣────────────────────────────────────────────
@tasks.loop(hours=1)
async def refresh_all_caches():

    # Removed first-run skip logic so cache loads immediately
    await load_all_cache(bot)

    # Clear processed message ID sets to prevent memory bloat
    clear_processed_messages_cache()


# ---- Simple health check command ----
@bot.tree.command(name="ping_test", description="Check if the bot is alive")
@app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
async def ping_test(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)


# --- Load Extensions / Cogs ----
async def load_extensions():
    """
    Dynamically load all Python files in the 'cogs' folder (ignores __pycache__).
    Logs loaded cogs with pretty_log and errors if loading fails.
    """
    loaded_cogs = []
    for root, dirs, files in os.walk("cogs"):
        # Skip __pycache__ folders
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                # Skip pokemons.py specifically in the cogs folder
                if root == "cogs" and file == "pokemons.py":
                    continue
                module_path = (
                    os.path.join(root, file).replace(os.sep, ".").replace(".py", "")
                )
                try:
                    await bot.load_extension(module_path)
                    loaded_cogs.append(module_path)
                except Exception as e:
                    pretty_log(
                        message=f"❌ Failed to load cog: {module_path}\n{e}",
                        tag="error",
                    )
    _loaded_count = len(loaded_cogs)
    pretty_log("ready", f"✅ Loaded { _loaded_count} cogs")#


# ---- Lifecycle ----#
@bot.event
async def on_ready():
    # Guard for type checker: bot.user may be Optional
    user = bot.user
    if user is None:
        pretty_log("info", "Bot is online (user not yet cached).")
    else:
        pretty_log("info", f"Bot online as {user} (ID: {user.id})")

    try:
        # Fast guild-only sync
        await bot.tree.sync(guild=discord.Object(id=DEFAULT_GUILD_ID))
        pretty_log("info", f"Slash commands synced to guild {DEFAULT_GUILD_ID}")
    except Exception as e:
        pretty_log("error", f"Slash sync failed: {e}")

    # Sync commands to VNA server
    try:
        await bot.tree.sync(guild=discord.Object(id=VNA_SERVER_ID))
        pretty_log("info", f"Slash commands synced to guild {VNA_SERVER_ID}")
    except Exception as e:
        pretty_log("error", f"Slash sync to VNA server failed: {e}")

    # Start the hourly cache refresh task
    if not refresh_all_caches.is_running():
        refresh_all_caches.start()
        pretty_log(message="✅ Started hourly cache refresh task", tag="ready")

    try:
        await bot.change_presence(
            activity=discord.Game(name="/auction_list • /auction_bid")
        )
    except Exception:
        pass


# ---- Boot ----
async def main():
    # Load extensions
    await load_extensions()

    # Intialize the database pool
    try:
        bot.pg_pool = await get_pg_pool()
        pretty_log(message="✅ PostgreSQL connection pool established", tag="ready")
    except Exception as e:
        pretty_log(
            tag="critical",
            message=f"Failed to initialize database pool: {e}",
            include_trace=True,
        )
        return  # Exit if DB connection fails
    # Start the scheduler
    # await setup_scheduler(bot)

    # Register persistent views
    # await register_persistent_views(bot)

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("❌ DISCORD_TOKEN environment variable is not set.")

    await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pretty_log("info", "Shutting down...")
