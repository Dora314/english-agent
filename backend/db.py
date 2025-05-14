# backend/db.py
import asyncio
from prisma import Prisma
from prisma.errors import PrismaError  # Import for more specific error handling if needed

# Global Prisma client instance
# It's better to initialize it as None and connect in startup,
# or use a context manager for requests if you prefer request-scoped sessions.
# For simplicity with FastAPI's Depends, a global instance managed by startup/shutdown is common.
prisma_client = Prisma(auto_register=True) # auto_register=True is helpful for some environments

async def connect_prisma():
    """Connects the global Prisma client if not already connected."""
    if not prisma_client.is_connected():
        try:
            print("Attempting to connect Prisma client...")
            await prisma_client.connect()
            print("Prisma client connected successfully.")
        except Exception as e:
            print(f"Failed to connect Prisma client: {e}")
            # Depending on your app's needs, you might want to raise the exception
            # or handle it in a way that allows the app to start but with DB issues flagged.
            raise # Re-raise the exception to make startup fail if DB is critical

async def disconnect_prisma():
    """Disconnects the global Prisma client if connected."""
    if prisma_client.is_connected():
        try:
            print("Attempting to disconnect Prisma client...")
            await prisma_client.disconnect()
            print("Prisma client disconnected successfully.")
        except Exception as e:
            print(f"Error during Prisma client disconnection: {e}")

async def get_db() -> Prisma:
    """
    Dependency function to get a Prisma client instance.
    Ensures the client is connected.
    """
    if not prisma_client.is_connected():
        # This scenario should ideally be handled by the startup event,
        # but as a fallback, attempt to connect.
        print("Prisma client not connected in get_db, attempting to connect...")
        await connect_prisma() # This might raise an error if connection fails
    return prisma_client

# Example of how you might use Prisma errors if needed:
# async def example_db_operation(db: Prisma):
#     try:
#         user = await db.user.find_first()
#         return user
#     except PrismaError as e:
#         print(f"A Prisma-specific error occurred: {e}")
#         raise
#     except Exception as e:
#         print(f"A general error occurred: {e}")
#         raise