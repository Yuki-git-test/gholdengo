import zoneinfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


# 🛠️ Scheduler Manager for Background Tasks
class SchedulerManager:
    def __init__(self, timezone_str="Asia/Manila"):
        self.timezone = zoneinfo.ZoneInfo(timezone_str)
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)
        self.jobs = {}

    def start(self):
        self.scheduler.start()

    def add_cron_job(
        self,
        func,
        name,
        hour,
        minute,
        day_of_week=None,
        day_of_month=None,  # ← monthly support
        args=None,
        timezone=None,  # ← NEW optional timezone
        replace_existing=True,
    ):
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            day=day_of_month,  # APScheduler uses `day` internally for day-of-month
            timezone=timezone or self.timezone,  # ← fallback to default Manila
        )
        job = self.scheduler.add_job(
            func, trigger, args=args or [], id=name, replace_existing=replace_existing
        )
        self.jobs[name] = job
        return job

    def add_job(self, func, trigger, args=None, id=None, replace_existing=True):
        job = self.scheduler.add_job(
            func, trigger, args=args or [], id=id, replace_existing=replace_existing
        )
        if id:
            self.jobs[id] = job
        return job

    def remove_job(self, name):
        if name in self.jobs:
            self.scheduler.remove_job(name)
            del self.jobs[name]

    def shutdown(self):
        self.scheduler.shutdown()
