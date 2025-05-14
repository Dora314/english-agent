import asyncio
from prisma import Prisma
from routers.mcqs import dummy_questions_data # Assuming mcqs.py is accessible
import json # Import the json module

async def main():
    db = Prisma()
    await db.connect()

    # Delete all existing questions
    print("Deleting existing questions...")
    await db.question.delete_many()
    print("Existing questions deleted.")

    print("Seeding questions...")

    for topic, questions_in_topic in dummy_questions_data.items():
        print(f"  Topic: {topic}")
        for q_data in questions_in_topic:
            # Check if question already exists by ID to avoid duplicates if script is run multiple times
            existing_question = await db.question.find_unique(where={"id": q_data.id})
            if existing_question:
                print(f"    Question ID {q_data.id} already exists, skipping.")
                continue

            print(f"    Seeding question ID: {q_data.id} - {q_data.question_text[:30]}...")
            await db.question.create(
                data={
                    "id": q_data.id,
                    "questionText": q_data.question_text,
                    "options": json.dumps([{"id": opt.id, "text": opt.text} for opt in q_data.options]), # Explicitly dump to JSON string
                    "correctAnswerId": q_data.correctOptionId,
                    # "topicId": "some_topic_id_if_you_seed_topics_table_too",
                    # "difficultyLevel": "easy" 
                }
            )
    print("Seeding complete.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
