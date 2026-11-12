from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.scheduler import compute_next_run
from app.database import get_db
from app.models.scan import Schedule
from app.schemas.scan import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse
)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(schedule_data: ScheduleCreate, db: Session = Depends(get_db)):
    """
    Create a new scheduled scan.
    
    Args:
        schedule_data: Schedule configuration
        db: Database session
        
    Returns:
        Created schedule object
    """
    schedule = Schedule(
        name=schedule_data.name,
        description=schedule_data.description,
        scan_config=schedule_data.scan_config,
        cron_expression=schedule_data.cron_expression,
        enabled=schedule_data.enabled,
        next_run_at=(
            compute_next_run(schedule_data.cron_expression)
            if schedule_data.enabled
            else None
        ),
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return schedule


@router.get("", response_model=List[ScheduleResponse])
def list_schedules(
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all scheduled scans.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        enabled_only: Only return enabled schedules
        db: Database session
        
    Returns:
        List of schedules
    """
    query = db.query(Schedule)
    
    if enabled_only:
        query = query.filter(Schedule.enabled == True)
    
    schedules = query.order_by(Schedule.created_at.desc()).offset(skip).limit(limit).all()
    
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """
    Get schedule details by ID.
    
    Args:
        schedule_id: Schedule ID
        db: Database session
        
    Returns:
        Schedule object
    """
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found"
        )
    
    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    schedule_update: ScheduleUpdate,
    db: Session = Depends(get_db)
):
    """
    Update schedule details.
    
    Args:
        schedule_id: Schedule ID
        schedule_update: Update data
        db: Database session
        
    Returns:
        Updated schedule object
    """
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found"
        )
    
    # Update fields
    if schedule_update.name is not None:
        schedule.name = schedule_update.name
    if schedule_update.description is not None:
        schedule.description = schedule_update.description
    if schedule_update.scan_config is not None:
        schedule.scan_config = schedule_update.scan_config
    if schedule_update.cron_expression is not None:
        schedule.cron_expression = schedule_update.cron_expression
    if schedule_update.enabled is not None:
        schedule.enabled = schedule_update.enabled

    # Keep next_run_at consistent with cron/enabled changes.
    if not schedule.enabled:
        schedule.next_run_at = None
    elif (
        schedule_update.cron_expression is not None
        or schedule_update.enabled is not None
        or schedule.next_run_at is None
    ):
        schedule.next_run_at = compute_next_run(schedule.cron_expression)

    schedule.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(schedule)
    
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """
    Delete a schedule.
    
    Args:
        schedule_id: Schedule ID
        db: Database session
    """
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found"
        )
    
    db.delete(schedule)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
