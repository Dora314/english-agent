from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from db import get_db
from auth import get_current_user_id_from_header

router = APIRouter()

@router.delete("/me/data", status_code=200, tags=["Users"])
async def delete_user_learning_data(
    db: Prisma = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_from_header)
):
    """
    Deletes all personalized learning data for the authenticated user.
    This includes their answers, wrongdoing questions, and resets their dashboard data.
    """
    if not current_user_id:
        raise HTTPException(status_code=403, detail="Not authenticated")

    try:
        # Start a transaction
        async with db.tx() as transaction:
            # Delete UserAnswers
            await transaction.useranswer.delete_many(
                where={"userId": current_user_id}
            )
            print(f"Deleted UserAnswers for user {current_user_id}")

            # Delete UserWrongdoingQuestions
            await transaction.userwrongdoingquestion.delete_many(
                where={"userId": current_user_id}
            )
            print(f"Deleted UserWrongdoingQuestions for user {current_user_id}")

            # Reset UserDashboardData
            await transaction.userdashboarddata.update(
                where={"userId": current_user_id},
                data={
                    "totalPoints": 0,
                    "previousSessionPoints": 0,
                    "pointsHistory": "[]",  # Reset to an empty JSON array as a string
                }
            )
            print(f"Reset UserDashboardData for user {current_user_id}")
            
        return {"message": "Personalized learning data successfully deleted."}

    except Exception as e:
        print(f"Error deleting learning data for user {current_user_id}: {e}")
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting data: {str(e)}")

