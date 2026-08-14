from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta, timezone
from dateutil.rrule import rrulestr
from bson.objectid import ObjectId
from models.time_management import RoutineCreate, TaskStatus, TaskCreate, ProjectCreate

from core.database import routine_collection, task_collection, project_collection
from api.deps import require_user

router = APIRouter()

async def recalculate_project_health(project_id: str, user_id_string: str):
    """A background helper to instantly update project health in the database."""
    project = await project_collection.find_one({"_id": ObjectId(project_id), "user_id": user_id_string})
    if not project: return

    # Fetch tasks
    tasks = await task_collection.find({"project_id": project_id, "user_id": user_id_string}).to_list(length=1000)
    total_tasks = len(tasks)
    if total_tasks == 0: return

    # Work progress
    completed_tasks = sum(1 for task in tasks if task.get("status") == TaskStatus.COMPLETED.value)
    work_progress = (completed_tasks / total_tasks)

    # Time progress
    now = datetime.now(timezone.utc)
    created_at = project["created_at"].replace(tzinfo=timezone.utc)
    deadline = project["deadline"].replace(tzinfo=timezone.utc)

    if now >= deadline:
        time_progress = 1.0
    else:
        total_duration = (deadline - created_at).total_seconds()
        time_elapsed = (now - created_at).total_seconds()
        time_progress = (time_elapsed / total_duration) if total_duration > 0 else 0.0
    
    # Health score
    health_score = (work_progress / time_progress) if time_progress > 0 else 1.0

    # Update the project health score in the database
    await project_collection.update_one(
        {"_id": ObjectId(project_id), "user_id": user_id_string},
        {"$set": {"health_score": min(health_score, 1.0)}}
    )
    

@router.post("/routines", status_code=201)
async def create_routine(
    routine_in : RoutineCreate, 
    current_user : dict = Depends(require_user)
    ):

    """
    Creates a Routine Blueprint and automatically spawns the corresponding Tasks.
    """    
    
    # Extract the user_id from MongoDB
    user_id_string = str(current_user["_id"])

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
            "user_id": user_id_string,
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

@router.get("/timeline/{target_date}")
async def get_daily_timeline(
    target_date: str,
    offset: int = Query(0, description="Timezone offset in minutes from UTC"),
    current_user: dict = Depends(require_user)
):
    """
    Fetches all tasks for a specific date and calculates the free-time slots between them.
    """
    user_id_string = str(current_user["_id"])
    # Build the time fence (Start and end of the target date)
    try:
        parsed_date = datetime.strptime(target_date, "%Y-%m-%d")

        local_start = parsed_date.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
        local_end = parsed_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

        start_of_day = local_start - timedelta(minutes=offset)
        end_of_day = local_end - timedelta(minutes=offset)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    # Fetch and sort the tasks
    cursor = task_collection.find({
        "user_id": user_id_string,
        "start_time": {"$gte": start_of_day, "$lte": end_of_day}
    }).sort("start_time", 1)

    tasks = await cursor.to_list(length=1000)
    
    # The whitespace calculation logic
    timeline = []
    current_time_pointer = start_of_day

    total_tasks = len(tasks)
    completed_tasks = 0
    total_free_minutes = 0

    for task in tasks:
        task_start = task["start_time"].replace(tzinfo=timezone.utc) - timedelta(minutes=offset)
        task_end = task["end_time"].replace(tzinfo=timezone.utc) - timedelta(minutes=offset)

        if task.get("status") == TaskStatus.COMPLETED.value:
            completed_tasks += 1
        
        if task_start > current_time_pointer:
            gap_duration = (task_start - current_time_pointer).total_seconds() / 60
            total_free_minutes += gap_duration

            timeline.append({
                "type": "free_slot",
                "start_time": current_time_pointer.isoformat(),
                "end_time": task_start.isoformat(),
                "duration_minutes": gap_duration
            })

        timeline.append({
            "type": "task",
            "id": str(task["_id"]),
            "title": task["title"],
            "description": task.get("description"),
            "start_time": task_start.isoformat(),
            "end_time": task_end.isoformat(),
            "status": task.get("status"),
            "is_exact_time": task.get("is_exact_time"),
            "routine_id": task.get("routine_id"),
            "project_id": task.get("project_id")
        })

        current_time_pointer = max(current_time_pointer, task_end)
    
    # Handle the final gap at the end of the day
    if current_time_pointer < end_of_day:
        final_gap_duration = (end_of_day - current_time_pointer).total_seconds() / 60
        total_free_minutes += final_gap_duration

        timeline.append({
            "type": "free_slot",
            "start_time": current_time_pointer.isoformat(),
            "end_time": end_of_day.isoformat(),
            "duration_minutes": final_gap_duration
        })

    # Return the packaged payload
    return {
        "date": target_date,
        "summary": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "total_free_minutes": total_free_minutes
        },
        "timeline": timeline
    }

@router.post("/tasks", status_code=201)
async def create_standalone_task(
    task_in: TaskCreate,
    current_user: dict = Depends(require_user)
):
    """
    Creates a single, non-recurring task on the timeline.
    """
    user_id_string = str(current_user["_id"])

    # Convert the pydantic model to a dictionary
    task_dict = task_in.model_dump()
    # Securely inject the user_id and set the default status
    task_dict["user_id"] = user_id_string
    task_dict["status"] = TaskStatus.PENDING.value

    # Insert the task into the database
    insert_result = await task_collection.insert_one(task_dict)

    return {
        "message": "Task created successfully.",
        "task_id": str(insert_result.inserted_id)
    }

@router.patch("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: TaskStatus = Query(..., description="New status for the task"),
    current_user: dict = Depends(require_user)
):
    """
    Allows the user to check off a task on their timeline.
    """
    user_id_string = str(current_user["_id"])

    try:
        task_object_id = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task ID format.")
    
    update_result = await task_collection.update_one(
        {"_id": task_object_id, "user_id": user_id_string},
        {"$set": {"status": status.value}}
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found or already has this status.")
    
    # If the task is associated with a project, recalculate the project's health score
    task = await task_collection.find_one({"_id": task_object_id})
    if task and task.get("project_id"):
        await recalculate_project_health(task["project_id"], user_id_string)

    return {"message": f"Task marked as {status.value}. Project health score recalculated."}

@router.post("/projects", status_code=201)
async def create_project(
    project_in: ProjectCreate,
    current_user: dict = Depends(require_user)
):
    """Creates a new Project container."""
    user_id_string = str(current_user["_id"])

    project_dict = project_in.model_dump()
    project_dict["user_id"] = user_id_string
    project_dict["created_at"] = datetime.now(timezone.utc)
    project_dict["health_score"] = 1.0

    insert_result = await project_collection.insert_one(project_dict)

    return {
        "message": "Project created successfully.",
        "project_id": str(insert_result.inserted_id)
    }

@router.get("/projects/{project_id}/dashboard")
async def get_project_dashboard(
    project_id: str,
    current_user: dict = Depends(require_user)
):
    """Fetches the project, its tasks, and dynamically calculates the live Health Score."""
    user_id_string = str(current_user["_id"])

    try:
        object_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Project ID.")

    # fetch the project
    project = await project_collection.find_one({"_id": object_id, "user_id": user_id_string})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # fetch all tasks assigned to this project
    cursor = task_collection.find({"project_id": project_id, "user_id": user_id_string})
    tasks = await cursor.to_list(length=1000)

    # Calculate work progress (Actual)
    total_tasks = len(tasks)
    completed_tasks = sum(1 for task in tasks if task.get("status") == TaskStatus.COMPLETED.value)

    work_progress = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0

    # Calculate time progress (Expected)
    now = datetime.now(timezone.utc)
    created_at = project["created_at"].replace(tzinfo=timezone.utc)
    deadline = project["deadline"].replace(tzinfo=timezone.utc)

    # If the deadline has passed.
    if now >= deadline:
        time_progress = 1.0
    else:
        total_duration = (deadline - created_at).total_seconds()
        time_elapsed = (now - created_at).total_seconds()
        # Prevent division by zero if they just created it 1 milisecond ago
        time_progress = (time_elapsed / total_duration) if total_duration > 0 else 0.0

    # Calculate health score
    health_score = (work_progress / time_progress) if time_progress > 0 else 1.0
    visual_health_score = min(health_score, 1.0)

    await project_collection.update_one(
        {"_id": object_id, "user_id": user_id_string},
        {"$set": {"health_score": visual_health_score}}
    )

    project["_id"] = str(project["_id"])

    return {
        "project": project,
        "metrics": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "work_progress_percentage": round(work_progress * 100, 1),
            "time_elapsed_percentage": round(time_progress * 100, 1),
            "current_health_score": round(visual_health_score, 2),
            "status_tier": "CRITICAL" if visual_health_score < 0.5 else "WARNING" if visual_health_score < 0.8 else "HEALTHY"
        },
        "tasks": [{**t, "_id": str(t["_id"])} for t in tasks]
    }
