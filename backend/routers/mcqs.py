# backend/routers/mcqs.py
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict
import json
from datetime import datetime, timezone

from schemas import (
    GenerateMCQsRequest, GenerateMCQsResponse, QuestionResponse, MCQOption,
    SubmitAnswerRequest, SubmitAnswerResponse,
    SubmitQuizSessionRequest, SubmitQuizSessionResponse, DashboardDataResponse
)
from db import get_db
from prisma import Prisma

import sys
if ".." not in sys.path: sys.path.append("..")
from auth import get_current_user_id_from_header

from ai_core.agent import MainCoreAgent

router = APIRouter()
agent_instance = MainCoreAgent()

@router.post("/generate", response_model=GenerateMCQsResponse, tags=["MCQs"])
async def generate_mcqs_endpoint(
    payload: GenerateMCQsRequest = Body(...),
    db: Prisma = Depends(get_db)
):
    topic_string = payload.topic_string
    fixed_num_questions = 5 
    
    print(f"API: Request to generate {fixed_num_questions} MCQs for topic: '{topic_string}' using AI Agent with RAG.")

    # Call the RAG-enabled method from the agent, always with 5 questions
    ai_generated_mcqs_raw = agent_instance.generate_mcqs_with_rag(
        user_topic=topic_string,
        num_questions=fixed_num_questions
    )

    client_questions: List[QuestionResponse] = []
    generated_topic_id = f"ai_topic_{topic_string.lower().strip().replace(' ', '_')}"

    if not ai_generated_mcqs_raw:
        print(f"API: AI agent returned no structured questions for topic '{topic_string}'.")
        return GenerateMCQsResponse(questions=[], topic_id=f"{generated_topic_id}_no_questions_generated")

    for raw_mcq in ai_generated_mcqs_raw:
        question_text = raw_mcq.get("question_text")
        options_data = raw_mcq.get("options", [])
        correct_option_id = raw_mcq.get("correct_option_id")

        if not (question_text and options_data and correct_option_id and len(options_data) > 0):
            print(f"API: Warning - Skipping a malformed MCQ from AI (missing data): {raw_mcq}")
            continue
            
        try:
            new_db_question = await db.question.create(
                data={
                    "questionText": question_text,
                    "options": json.dumps(options_data), # Explicitly serialize to JSON string
                    "correctAnswerId": correct_option_id,
                    "topicId": generated_topic_id
                }
            )
            print(f"API: Saved question to DB with ID: {new_db_question.id}")

            client_options = [MCQOption(id=opt["id"], text=opt["text"]) for opt in options_data]
            
            client_questions.append(QuestionResponse(
                id=new_db_question.id,
                question_text=new_db_question.questionText,
                options=client_options
            ))
        except Exception as e:
            print(f"API: Error saving question to DB or preparing client response: {e}")
            import traceback
            traceback.print_exc()
            continue

    if not client_questions and fixed_num_questions > 0 and ai_generated_mcqs_raw:
         print(f"API: No valid questions could be saved/processed from AI output for topic '{topic_string}'.")
         return GenerateMCQsResponse(questions=[], topic_id=f"{generated_topic_id}_processing_failed_for_all")
    
    print(f"API: Successfully generated and saved {len(client_questions)} MCQs for topic '{topic_string}'.")
    return GenerateMCQsResponse(questions=client_questions, topic_id=generated_topic_id)


@router.post("/answer", response_model=SubmitAnswerResponse, tags=["MCQs"])
async def submit_answer_endpoint(
    payload: SubmitAnswerRequest = Body(...),
    db: Prisma = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_from_header)
):
    print(f"User '{current_user_id}' submitted answer for Q: '{payload.question_id}', Selected: '{payload.selected_answer_id}'")

    db_question = await db.question.find_unique(where={"id": payload.question_id})

    if not db_question:
        print(f"Error: Question with ID '{payload.question_id}' not found in database.")
        raise HTTPException(status_code=404, detail=f"Question with ID {payload.question_id} not found.")

    is_correct = (db_question.correctAnswerId == payload.selected_answer_id)
    correct_option_text = ""
    
    if isinstance(db_question.options, list):
        for opt in db_question.options:
            if isinstance(opt, dict) and opt.get("id") == db_question.correctAnswerId:
                correct_option_text = opt.get("text", "")
                break
    
    print(f"Q: '{payload.question_id}' - DB Correct ID: '{db_question.correctAnswerId}', User Selected: '{payload.selected_answer_id}', IsCorrect: {is_correct}")

    try:
        print(f"Attempting to save UserAnswer for user '{current_user_id}', q_id '{payload.question_id}'")
        await db.useranswer.create(
            data={
                "userId": current_user_id,
                "questionId": payload.question_id,
                "selectedOptionId": payload.selected_answer_id,
                "isCorrect": is_correct,
            }
        )
        print(f"UserAnswer saved for q_id: {payload.question_id}")

        if not is_correct:
            print(f"Attempting to save/update UserWrongdoingQuestion for user '{current_user_id}', q_id '{payload.question_id}'")
            await db.userwrongdoingquestion.upsert(
                where={"userId_questionId": {"userId": current_user_id, "questionId": payload.question_id}},
                data={
                    "create": {
                        "userId": current_user_id,
                        "questionId": payload.question_id,
                        "retestedCorrectly": False,
                        "timestampMarkedWrong": datetime.now(timezone.utc)
                    },
                    "update": {
                        "timestampMarkedWrong": datetime.now(timezone.utc),
                        "retestedCorrectly": False
                    }
                }
            )
            print(f"UserWrongdoingQuestion saved/updated for q_id: '{payload.question_id}'.")
        elif is_correct: 
            existing_wrongdoing_entry = await db.userwrongdoingquestion.find_unique(
                where={"userId_questionId": {"userId": current_user_id, "questionId": payload.question_id}}
            )
            if existing_wrongdoing_entry and not existing_wrongdoing_entry.retestedCorrectly:
                await db.userwrongdoingquestion.update(
                    where={"id": existing_wrongdoing_entry.id},
                    data={"retestedCorrectly": True}
                )
                print(f"UserWrongdoingQuestion for q_id: '{payload.question_id}' marked as retestedCorrectly.")
        
        user_dashboard = await db.userdashboarddata.find_unique(where={"userId": current_user_id})
        current_total_points = user_dashboard.totalPoints if user_dashboard else 0

        return SubmitAnswerResponse(
            is_correct=is_correct,
            correct_answer_id=db_question.correctAnswerId,
            correct_answer_text=correct_option_text,
            current_points=current_total_points
        )

    except Exception as e:
        print(f"Error during answer processing for user '{current_user_id}', Q: '{payload.question_id}': {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/session/submit", response_model=SubmitQuizSessionResponse, tags=["MCQs Quiz Session"])
async def submit_quiz_session_endpoint(
    payload: SubmitQuizSessionRequest = Body(...),
    db: Prisma = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_from_header)
):
    print(f"--- SUBMIT QUIZ SESSION START ---")
    print(f"User {current_user_id} submitted quiz session. Topic: {payload.topic_id}")
    print(f"Received answers_map: {payload.answers_map}")

    session_points_earned = 0
    points_per_correct_answer = 10 

    for question_id, selected_option_id in payload.answers_map.items():
        print(f"Processing Q_ID: {question_id}, Selected_Option_ID: {selected_option_id}")
        
        db_question = await db.question.find_unique(where={"id": question_id})
        
        if not db_question:
            print(f"  WARNING: Question with ID '{question_id}' NOT FOUND in database. Skipping.")
            continue

        print(f"  Found DB question: ID={db_question.id}, CorrectOptionID={db_question.correctAnswerId}")
        if db_question.correctAnswerId == selected_option_id:
            session_points_earned += points_per_correct_answer
            print(f"  CORRECT. Points for this question: {points_per_correct_answer}. Current session_points_earned: {session_points_earned}")
        else:
            print(f"  INCORRECT. Points for this question: 0. Current session_points_earned: {session_points_earned}")
    
    print(f"Total session points earned for user {current_user_id}: {session_points_earned}")
    print(f"--- END OF POINTS CALCULATION ---")

    try:
        dashboard_data = await db.userdashboarddata.find_unique(where={"userId": current_user_id})

        new_history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "points": session_points_earned,
            "topic_id": payload.topic_id or "unknown_topic"
        }

        if not dashboard_data:
            print(f"No dashboard data found for user {current_user_id}, creating new record.")
            dashboard_data = await db.userdashboarddata.create(
                data={
                    "userId": current_user_id,
                    "totalPoints": session_points_earned,
                    "previousSessionPoints": session_points_earned,
                    "pointsHistory": json.dumps([new_history_entry])
                }
            )
        else:
            try:
                current_history = json.loads(dashboard_data.pointsHistory) if dashboard_data.pointsHistory else []
            except json.JSONDecodeError:
                print(f"Warning: Could not parse pointsHistory for user {current_user_id}. Resetting history.")
                current_history = []

            current_history.append(new_history_entry)
            max_history_items = 50 
            if len(current_history) > max_history_items:
                current_history = current_history[-max_history_items:]

            dashboard_data = await db.userdashboarddata.update(
                where={"userId": current_user_id},
                data={
                    "totalPoints": dashboard_data.totalPoints + session_points_earned,
                    "previousSessionPoints": session_points_earned,
                    "pointsHistory": json.dumps(current_history)
                }
            )
        
        print(f"Dashboard data updated for user {current_user_id}.")
        
        response_dashboard_data = DashboardDataResponse(
            user_id=dashboard_data.userId,
            total_points=dashboard_data.totalPoints,
            previous_session_points=dashboard_data.previousSessionPoints,
            points_history=json.loads(dashboard_data.pointsHistory),
            last_5_wrong_questions=[]
        )

        return SubmitQuizSessionResponse(
            message="Quiz session submitted successfully and dashboard updated.",
            session_points_earned=session_points_earned,
            updated_dashboard_data=response_dashboard_data
        )

    except Exception as e:
        print(f"Error updating dashboard data for user {current_user_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update dashboard: {str(e)}")