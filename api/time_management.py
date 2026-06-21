from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, timezone
from dateutil.rrule import rrulestr
from models.time_management import RoutineCreate, TaskStatus

from core.database import routine_collection, task_collection

router = APIRouter()

@router.post("/routines", status_code=201)
async def create_routine(routine_in: RoutineCreate):
    """
    Creates a Routine Blueprint and automatically spawns the corresponding Tasks.
    """
    # Save the blueprint
    routine_dict = routine_in.model_dump()
    routine_dict["preferred_start_time"] = routine_dict["preferred_start_time"].isoformat()
    insert_result = await routine_collection.insert_one(routine_dict)
    routine_id = str(insert_result.inserted_id)

    # The spawning logic - Generate tasks based on the rrule
    max_horizon = datetime.now(timezone.utc) + timedelta(days=90)  # Limit to 90 days for safety

    if routine_in.end_date and routine_in.end_date < max_horizon:
        cutoff_date = routine_in.end_date
    else:
        cutoff_date = max_horizon
    
    try:
        rule = rrulestr(routine_in.rrule, dtstart=routine_in.start_date)
        generated_datetimes = list(rule.between(routine_in.start_date, cutoff_date, inc=True))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid RRULE format: {str(e)}")
    
    # Create the tasks
    tasks_to_insert = []

    for task_start_time in generated_datetimes:

        task_end_time = task_start_time + timedelta(minutes=routine_in.duration_minutes)

        new_task = {
            "user_id": routine_in.user_id,
            "title": routine_in.title,
            "description": routine_in.description,
            "start_time": task_start_time,
            "end_time": task_end_time,
            "is_exact_time": routine_in.is_exact_time,
            "status": TaskStatus.PENDING.value,
            "routine_id": routine_id,
            "project_id": None 
        }

        tasks_to_insert.append(new_task)
    
    # Bulk insert the tasks
    if tasks_to_insert:
        await task_collection.insert_many(tasks_to_insert)
    
    return {
        "message": "Routine created and tasks spawned successfully.",
        "routine_id": routine_id,
        "tasks_spawned": len(tasks_to_insert)
    }