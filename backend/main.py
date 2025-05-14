# backend/main.py
import shutil
import os
import uuid
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Request
)
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv # To load .env file for BACKEND_BASE_URL if needed

from db import get_db, connect_prisma, disconnect_prisma # Prisma utility functions
from prisma import Prisma # Prisma client type for type hinting

from auth import get_current_user_id_from_header # Added import from auth.py
from routers import mcqs as mcq_router # Assuming routers/mcqs.py structure
from routers import dashboard as dashboard_router # Add this import
from routers import retest as retest_router # Add this import
from routers import users as users_router # Add this import

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file in the backend directory

# --- Configuration ---
BACKEND_HOST = os.getenv("BACKEND_HOST", "localhost")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", f"http://{BACKEND_HOST}:{BACKEND_PORT}")

# Define paths relative to this main.py file or an absolute path
# Path(__file__).resolve().parent gives the directory of main.py
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
AVATARS_DIR = STATIC_DIR / "avatars"

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="English MCQ Platform API",
    description="API for the Personalized English MCQ Learning Platform.",
    version="0.1.0"
)

# --- Middleware ---
# CORS (Cross-Origin Resource Sharing)
origins = [
    "http://localhost:3000",  # Next.js frontend
    "http://localhost:8000",  # Backend itself (if it ever calls its own APIs)
    # Add any other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specified origins
    allow_credentials=True, # Allows cookies to be included in requests
    allow_methods=["*"],    # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)

# --- Static Files ---
# Mount the static directory to serve files like uploaded avatars
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Event Handlers for Prisma Connection ---
@app.on_event("startup")
async def startup_event():
    print("FastAPI application startup...")
    try:
        await connect_prisma()
    except Exception as e:
        print(f"CRITICAL: Database connection failed on startup: {e}")
        # You might want to prevent the app from fully starting or log this severely
        # For now, it will print and the app will continue starting,
        # but endpoints requiring DB will fail.

@app.on_event("shutdown")
async def shutdown_event():
    print("FastAPI application shutdown...")
    await disconnect_prisma()


# --- API Endpoints ---
@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the API."""
    return {"message": "Welcome to the English MCQ Platform API!"}


@app.put("/api/users/me/avatar", tags=["Users"])
async def upload_avatar(
    file: UploadFile = File(..., description="Avatar image file (PNG, JPG, GIF, WEBP)"),
    db: Prisma = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_from_header)
):
    """
    Uploads or updates the avatar for the authenticated user.
    The user ID is expected in the 'X-User-ID' header (for this placeholder auth).
    """
    print(f"Received avatar upload request for user: {current_user_id}")
    print(f"Uploaded file: {file.filename}, content type: {file.content_type}")

    # Validate file type (server-side validation is important)
    allowed_content_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type: '{file.content_type}'. Only JPG, PNG, GIF, WEBP allowed."
        )

    # Validate file size (e.g., max 2MB)
    max_size = 2 * 1024 * 1024  # 2 MB
    size = await file.read() # Read the file content to get its size
    await file.seek(0) # Reset the file pointer to the beginning for saving
    if len(size) > max_size:
        raise HTTPException(
            status_code=413, # Payload Too Large
            detail=f"File too large. Maximum size is {max_size // 1024 // 1024}MB."
        )

    # Generate a unique filename to prevent overwrites and ensure URL-friendliness
    file_extension = Path(file.filename).suffix.lower() # Ensure lowercase extension
    if not file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']: # Double check extension
        file_extension = ".png" # Default to png if extension is weird or missing

    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path_on_server = AVATARS_DIR / unique_filename
    print(f"Attempting to save avatar to: {file_path_on_server}")

    try:
        # Save the file to the server
        with open(file_path_on_server, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved successfully: {file_path_on_server}")
    except Exception as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save image file: {str(e)}")
    finally:
        await file.close() # Ensure the uploaded file is closed

    # Construct the publicly accessible URL for the saved avatar
    # This depends on how your static files are served and your BACKEND_BASE_URL
    # It should be /static/avatars/unique_filename because of app.mount("/static", ...)
    avatar_public_url = f"{BACKEND_BASE_URL}/static/avatars/{unique_filename}"
    print(f"Avatar public URL: {avatar_public_url}")

    try:
        # Update user's avatar_url in the database
        # Note: Your Prisma schema uses 'image' for the avatar URL field on the User model
        updated_user = await db.user.update(
            where={"id": current_user_id},
            data={"image": avatar_public_url}
        )

        if not updated_user:
            # This would be unusual if current_user_id was validated, but handle defensively
            if file_path_on_server.exists():
                os.remove(file_path_on_server) # Clean up orphaned file
            print(f"User with ID {current_user_id} not found in database during update.")
            raise HTTPException(status_code=404, detail="User not found, avatar update failed.")

        print(f"Database updated successfully for user {current_user_id} with new avatar URL.")
        # Select only specific fields to return if needed, to avoid sending sensitive data
        # For now, returning the full updated_user object from Prisma is fine for testing
        return {
            "message": "Avatar updated successfully",
            "avatarUrl": avatar_public_url,
            "user": { # Example of shaping the user response
                "id": updated_user.id,
                "name": updated_user.name,
                "email": updated_user.email,
                "image": updated_user.image
            }
        }
    except Exception as e:
        # Clean up the saved file if database update fails to prevent orphaned files
        if file_path_on_server.exists():
            os.remove(file_path_on_server)
        print(f"Error updating database for user {current_user_id}: {e}")
        # Consider more specific error handling for Prisma errors if needed
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")


# Include the MCQ router
app.include_router(
    mcq_router.router, # Use mcq_router.router
    prefix="/api/mcqs", # All routes in mcqs.py will be prefixed with /api/mcqs
    tags=["MCQs Quiz Session"]       # Tag for OpenAPI docs
)
app.include_router(dashboard_router.router, prefix="/api/dashboard", tags=["Dashboard"]) # Add this line
app.include_router(retest_router.router, prefix="/api/retest", tags=["Retest"]) # Add this line
app.include_router(users_router.router, prefix="/api/users", tags=["Users"]) # Add this line

# --- Add other routers or endpoints below as needed ---
# For example:
# from .routers import mcqs, dashboard # Assuming you create these later
# app.include_router(mcqs.router, prefix="/api/mcqs", tags=["MCQs"])
# app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

if __name__ == "__main__":
    # This block is for running directly with `python main.py` (less common for FastAPI dev)
    # Usually, you run with `uvicorn main:app --reload`
    import uvicorn
    print(f"Starting Uvicorn server on {BACKEND_HOST}:{BACKEND_PORT}")
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)