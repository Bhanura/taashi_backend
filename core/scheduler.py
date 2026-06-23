# core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone
from dateutil.rrule import rrulestr
from core.database import routine_collection, task_collection
from models.time_management import TaskStatus

# Initialize the Async Scheduler
scheduler = AsyncIOScheduler()

async def spawn_future_routine_tasks():
    """
    The Cron Job: Wakes up and checks if any routines are running out of tasks.
    """
    print("🤖 [CRON] Waking up to check Routine Horizons...")
    
    now = datetime.now(timezone.utc)
    # We want to make sure the user always has at least 30 days of tasks generated ahead of time
    minimum_horizon = now + timedelta(days=30) 

    # 1. Fetch all active routines from the database
    # (In a massive app, you'd filter out routines where end_date is in the past)
    async for routine in routine_collection.find({}):
        routine_id = str(routine["_id"])
        
        # 2. Find the VERY LAST task generated for this specific routine
        # We sort by 'start_time' descending (-1) and grab the first one
        latest_task = await task_collection.find_one(
            {"routine_id": routine_id}, 
            sort=[("start_time", -1)]
        )

        if not latest_task:
            continue # Skip if this routine has no tasks for some reason

        # We must make sure the database datetime has timezone info
        latest_task_time = latest_task["start_time"].replace(tzinfo=timezone.utc)

        # 3. Does it need a refill?
        if latest_task_time < minimum_horizon:
            print(f"🔄 [CRON] Refilling tasks for routine: {routine['title']}")
            
            # Start generating from the day AFTER the last task
            new_start_date = latest_task_time + timedelta(minutes=1) # Add a minute to avoid overlap
            new_cutoff = new_start_date + timedelta(days=60) # Generate 60 more days
            
            # Respect the user's original end_date if it exists
            if routine.get("end_date"):
                routine_end = routine["end_date"].replace(tzinfo=timezone.utc)
                if routine_end < new_cutoff:
                    new_cutoff = routine_end
            
            if new_start_date > new_cutoff:
                continue # We've reached the end of the routine's life!

            # We only use 'search_start_time' for the .between() filter!
            original_anchor = routine["start_date"].replace(tzinfo=timezone.utc)

            # 4. Run the exact same RRULE math we used in the API!
            try:
                rule = rrulestr(routine["rrule_string"], dtstart=original_anchor)
                generated_datetimes = list(rule.between(new_start_date, new_cutoff, inc=True))
            except Exception as e:
                print(f"⚠️ [CRON] RRULE Error for {routine['title']}: {e}")
                continue

            # 5. Build and save the new cookies!
            tasks_to_insert = []
            for task_start_time in generated_datetimes:
                task_end_time = task_start_time + timedelta(minutes=routine["duration_minutes"])
                
                new_task = {
                    "user_id": routine["user_id"],
                    "title": routine["title"],
                    "description": routine.get("description"),
                    "start_time": task_start_time,
                    "end_time": task_end_time,
                    "is_exact_time": routine["is_exact_time"],
                    "status": TaskStatus.PENDING.value,
                    "routine_id": routine_id,
                    "project_id": None
                }
                tasks_to_insert.append(new_task)

            if tasks_to_insert:
                await task_collection.insert_many(tasks_to_insert)
                print(f"✅ [CRON] Added {len(tasks_to_insert)} new tasks for {routine['title']}")

# --- Schedule the Job ---
# This tells the robot to run this function every single day at 2:00 AM
scheduler.add_job(spawn_future_routine_tasks, 'cron', hour=2, minute=0)

# (For testing right now, you can uncomment the line below to make it run every 1 minute so you can watch it work!)
# scheduler.add_job(spawn_future_routine_tasks, 'interval', minutes=1)