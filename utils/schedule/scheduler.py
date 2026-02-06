import zoneinfo
from datetime import datetime
from zoneinfo import ZoneInfo

from utils.logs.pretty_log import pretty_log
from utils.schedule.schedule_helper import SchedulerManager

NYC = zoneinfo.ZoneInfo("America/New_York")  # auto-handles EST/EDT

# 🛠️ Create a SchedulerManager instance with Asia/Manila timezone
scheduler_manager = SchedulerManager(timezone_str="Asia/Manila")

# 🍥──────────────────────────────────────────────
# Scheduled Tasks Imports
# 🍥──────────────────────────────────────────────
from .monthly_donation_reset import reset_monthly_donation_sched


def format_next_run_manila(next_run_time):
    """
    Converts a timezone-aware datetime to Asia/Manila time and returns a readable string.
    """
    if next_run_time is None:
        return "No scheduled run time."
    # Convert to Manila timezone
    manila_tz = ZoneInfo("Asia/Manila")
    manila_time = next_run_time.astimezone(manila_tz)
    # Format as: Sunday, Nov 3, 2025 at 12:00 PM (Asia/Manila)
    return manila_time.strftime("%A, %b %d, %Y at %I:%M %p (Asia/Manila)")


# 🌈─────────────────────────────────────────────────────────────
# 💙 Ghouldengo Setup (setup_scheduler)
# 🌈─────────────────────────────────────────────────────────────
async def setup_scheduler(bot):

    # Start the scheduler
    scheduler_manager.start()
    # ✨─────────────────────────────────────────────────────────
    # 🤍 Monthly Donation Reset Every 1st at 12:00 AM EST
    # ✨─────────────────────────────────────────────────────────
    try:
        monthly_donation_reset_job = scheduler_manager.add_cron_job(
            reset_monthly_donation_sched,
            "monthly_donation_reset",
            day_of_month=1,
            hour=0,
            minute=0,
            args=[bot],
            timezone=NYC,
        )
        readable_next_run = format_next_run_manila(
            monthly_donation_reset_job.next_run_time
        )
        pretty_log(
            tag="schedule",
            message=f"Monthly donation reset job scheduled at {readable_next_run}",
            bot=bot,
        )
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to schedule monthly donation reset job: {e}",
            bot=bot,
        )
