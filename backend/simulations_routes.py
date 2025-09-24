from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/api/admin")


@router.post("/init-simulations")
async def initialize_simulations():
    simulations = [
        # Keep payload minimal; actual seeding handled in server.py older path or here
    ]
    # No-op insert guard; kept for compatibility
    return {"message": "Init simulations route moved; using existing data"}


@router.post("/merge-simulation-questions")
async def merge_simulation_questions():
    updates = {}
    updated = 0
    for sim_id, payload in updates.items():
        res = await db.simulations.update_one(
            {"id": sim_id},
            {"$set": {k: v for k, v in payload.items()}},
        )
        if res.matched_count:
            updated += 1
    return {"message": f"Merged questions into {updated} existing simulations"}


