from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, time, timezone
from enum import Enum

# Enums (Locking down our specific choices)
class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    MISSED = "missed"

# Models
class Project(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    title: str
    description: Optional[str] = None
    deadline: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    health_score: float = 1.0

    model_config = ConfigDict(populate_by_name=True)

class Routine(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    title: str
    description: Optional[str] = None
    rrule: str

    start_date: datetime
    end_date: Optional[datetime] = None
    duration_minutes: int
    preferred_start_time: time
    is_exact_time: bool = False

    model_config = ConfigDict(populate_by_name=True)

class Task(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime  # Keep this in mind
    is_exact_time: bool = False
    status: TaskStatus = TaskStatus.PENDING

    project_id: Optional[str] = None
    routine_id: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)

# DATA TRANSFER OBJECTS - DTOs (What the frontend sends us)
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: datetime

class RoutineCreate(BaseModel):
    title: str
    description: Optional[str] = None
    rrule: str

    start_date: datetime
    end_date: Optional[datetime] = None
    duration_minutes: int
    preferred_start_time: time
    is_exact_time: bool = False

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime  # Keep this in mind
    is_exact_time: bool = False

    project_id: Optional[str] = None
    routine_id: Optional[str] = None