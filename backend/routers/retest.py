from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List
import json # For parsing options if stored as JSON string

from prisma import Prisma

from schemas import QuestionResponse, MCQOption 
from db import get_db
from auth import get_current_user_id_from_header

router = APIRouter()

class RetestGenerateRequest(BaseModel):
    num_questions: int

class RetestQuestionDetail(QuestionResponse):
    pass

class RetestGenerateResponse(BaseModel):
    questions: List[RetestQuestionDetail]

@router.post("/generate", response_model=RetestGenerateResponse, tags=["Retest"])
async def generate_retest_questions(
    payload: RetestGenerateRequest = Body(...),
    db: Prisma = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_from_header)
):
    """
    Fetches a specified number of questions that the user previously answered incorrectly
    and have not yet been retested correctly.
    """
    if payload.num_questions <= 0:
        raise HTTPException(status_code=400, detail="Number of questions must be positive.")

    print(f"Attempting to fetch {payload.num_questions} wrong questions for user {current_user_id} to retest.")

    wrong_questions_entries = await db.userwrongdoingquestion.find_many(
        where={
            "userId": current_user_id,
            "retestedCorrectly": False
        },
        take=payload.num_questions,
        order={
            "timestampMarkedWrong": "asc"
        },
        include={"question": True} 
    )

    if not wrong_questions_entries:
        print(f"No wrong questions found for user {current_user_id} that need retesting.")
        return RetestGenerateResponse(questions=[])

    retest_questions_details: List[RetestQuestionDetail] = []
    for wrongdoing_entry in wrong_questions_entries:
        question_db = wrongdoing_entry.question
        if question_db:
            raw_options = question_db.options
            parsed_mcq_options: List[MCQOption] = []

            if isinstance(raw_options, list):
                for opt_data in raw_options:
                    if isinstance(opt_data, dict) and "id" in opt_data and "text" in opt_data:
                        parsed_mcq_options.append(MCQOption(id=str(opt_data["id"]), text=str(opt_data["text"])))
                    else:
                        print(f"Warning: Malformed option data for question {question_db.id}: {opt_data}")
            else:
                print(f"Warning: Options for question {question_db.id} are not in list format: {raw_options}")
            
            retest_questions_details.append(
                RetestQuestionDetail(
                    id=question_db.id,
                    question_text=question_db.questionText,
                    options=parsed_mcq_options
                )
            )
        else:
            print(f"Warning: Question data not found for wrongdoing_entry.id {wrongdoing_entry.id} (linked questionId: {wrongdoing_entry.questionId})")

    print(f"Successfully fetched {len(retest_questions_details)} questions for retest session for user {current_user_id}.")
    return RetestGenerateResponse(questions=retest_questions_details)
