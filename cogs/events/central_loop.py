import asyncio

from discord.ext import commands

from utils.logs.pretty_log import pretty_log

# 🧹 Import your scheduled tasks
from utils.background_tasks.giveaway_end_checker import giveaway_end_checker

TEST_SECONDS = 1
ACTUAL_SECONDS = 60
TICK_INTERVAL = ACTUAL_SECONDS  # Change to TEST_SECONDS for testing


# 🍰──────────────────────────────
#   🎀 Cog: CentralLoop
#   Handles background tasks every 60 seconds
# 🍰──────────────────────────────
class CentralLoop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loop_task = None

    def cog_unload(self):
        if self.loop_task and not self.loop_task.done():
            self.loop_task.cancel()
            pretty_log(
                "warn",
                "Loop task cancelled on cog unload.",
                label="CENTRAL LOOP",
                bot=self.bot,
            )

    async def central_loop(self):
        """Background loop that ticks every 60 seconds"""
        await self.bot.wait_until_ready()
        pretty_log(
            "",
            "✅ Central loop started!",
            label="💸 CENTRAL LOOP",
            bot=self.bot,
        )
        while not self.bot.is_closed():
            try:
                """pretty_log(
                    "",
                    "🔂 Running background checks...",
                    label="💸 CENTRAL LOOP",
                    bot=self.bot,
                )"""

                # 🎁 Check and end due giveaways
                await giveaway_end_checker(self.bot)

            except Exception as e:
                pretty_log(
                    "error",
                    f"{e}",
                    label="CENTRAL LOOP ERROR",
                    bot=self.bot,
                )
            await asyncio.sleep(TICK_INTERVAL)  # ⏱ tick interval

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the loop automatically once the bot is ready"""
        if not self.loop_task:
            self.loop_task = asyncio.create_task(self.central_loop())


# ====================
# 🔹 Setup
# ====================
async def setup(bot: commands.Bot):
    cog = CentralLoop(bot)
    await bot.add_cog(cog)

    print("\n[📋 CENTRAL LOOP CHECKLIST] Scheduled tasks loaded:")
    print("  ─────────────────────────────────────────────")
    print("  ✅  🎁 giveaway_end_checker")
    print("  💸 CentralLoop ticking every 60 seconds!")
    print("  ─────────────────────────────────────────────\n")
