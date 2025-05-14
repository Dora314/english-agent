# backend/routers/dashboard.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
import json
from datetime import datetime # For type hinting if needed

from schemas import DashboardDataResponse, WrongdoingQuestionInfo # Adjust import if schemas.py is elsewhere
from db import get_db
from prisma import Prisma
# from ..auth import get_current_user_id_from_header # Adjust import for auth.py
import sys
if ".." not in sys.path: sys.path.append("..")
from auth import get_current_user_id_from_header


router = APIRouter()

@router.get("/", response_model=DashboardDataResponse, tags=["Dashboard"])
async def get_user_dashboard(
    db: Prisma = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_from_header)
):
    """
    Fetches all data required for the user's dashboard.
    """
    print(f"Fetching dashboard data for user: {current_user_id}")

    # 1. Fetch UserDashboardData
    dashboard_data_db = await db.userdashboarddata.find_unique(where={"userId": current_user_id})

    if not dashboard_data_db:
        # If no dashboard data exists, create a default one (or handle as error)
        # This should ideally be created upon user registration.
        print(f"No dashboard data for user {current_user_id}. Returning default/empty.")
        # For now, let's return default values if not found, but you might want to ensure it always exists.
        # Or, you could create it here if that's your app's logic.
        # For this example, if it's missing, we'll raise an error or provide defaults.
        # To be robust, let's try creating it if it's missing.
        try:
            dashboard_data_db = await db.userdashboarddata.create(
                data={
                    "userId": current_user_id,
                    "totalPoints": 0,
                    "previousSessionPoints": 0,
                    "pointsHistory": "[]"
                }
            )
            print(f"Created default dashboard data for user {current_user_id}")
        except Exception as e_create:
            print(f"Failed to create default dashboard data for {current_user_id}: {e_create}")
            raise HTTPException(status_code=404, detail=f"Dashboard data not found for user and could not be created.")


    # Parse pointsHistory from JSON string
    try:
        points_history_parsed = json.loads(dashboard_data_db.pointsHistory)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse pointsHistory for user {current_user_id}. Using empty list.")
        points_history_parsed = []

    # 2. Fetch Last 5 Wrongdoing Questions
    # We need to join with the Question table to get question_text
    wrong_questions_db = await db.userwrongdoingquestion.find_many(
        where={"userId": current_user_id},
        order={"timestampMarkedWrong": "desc"},  # Corrected: Prisma uses 'order'
        take=5,
        include={"question": True}  # Assuming you want to include question details
    )

    last_5_wrong_questions_info: List[WrongdoingQuestionInfo] = []
    for wq in wrong_questions_db:
        if wq.question: # Ensure the related question object exists
            # Provide a default if questionText is None
            question_text_val = wq.question.questionText if wq.question.questionText is not None else "Question text not available"
            
            timestamp_marked_wrong_val = "Timestamp not available"
            if wq.timestampMarkedWrong:
                try:
                    timestamp_marked_wrong_val = wq.timestampMarkedWrong.isoformat()
                except AttributeError:
                    # Log if timestampMarkedWrong is not a datetime object, though Prisma should handle types
                    print(f"Warning: UserWrongdoingQuestion id {wq.id} has invalid timestampMarkedWrong type.")
            
            last_5_wrong_questions_info.append(
                WrongdoingQuestionInfo(
                    question_id=wq.questionId, # Assuming wq.questionId is always valid
                    question_text=question_text_val,
                    timestamp_marked_wrong=timestamp_marked_wrong_val
                )
            )
        else:
            print(f"Warning: Wrongdoing question entry {wq.id} for user {current_user_id} has no associated question data.")


    return DashboardDataResponse(
        user_id=dashboard_data_db.userId,
        total_points=dashboard_data_db.totalPoints,
        previous_session_points=dashboard_data_db.previousSessionPoints,
        points_history=points_history_parsed,
        last_5_wrong_questions=last_5_wrong_questions_info
    )

@router.post("/reset", tags=["Dashboard"])
async def reset_user_dashboard(
    db: Prisma = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_from_header)
):
    """
    Resets the user's dashboard data, including points, history, and wrongdoing questions.
    """
    print(f"Resetting dashboard data for user: {current_user_id}")

    # 1. Update UserDashboardData
    await db.userdashboarddata.update(
        where={"userId": current_user_id},
        data={
            "totalPoints": 0,
            "previousSessionPoints": 0,
            "pointsHistory": "[]"
        }
    )
    print(f"Reset UserDashboardData for user {current_user_id}")

    # 2. Delete UserAnswer records
    await db.useranswer.delete_many(
        where={"userId": current_user_id}
    )
    print(f"Deleted UserAnswer records for user {current_user_id}")

    # 3. Delete UserWrongdoingQuestion records
    await db.userwrongdoingquestion.delete_many(
        where={"userId": current_user_id}
    )
    print(f"Deleted UserWrongdoingQuestion records for user {current_user_id}")

    return {"message": "Dashboard data reset successfully."}