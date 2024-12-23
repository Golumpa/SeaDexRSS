import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, Response
from models import Base, Snapshot
from rss_generator import generate_rss
from seadex_client import RestApiClient
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import engine, get_db

rest_client = RestApiClient()

ANILIST_API_URL = "https://graphql.anilist.co"

# This tool will not hit seadex within this timeframe from the last update and will just fetch from the cache instead
# this is to prevent unnecessary API calls as seadex isn't updated overly often
UPDATE_INTERVAL = timedelta(minutes=240)

# Store the last call time for each Anilist ID
# No point in storing this in the db as the data doesn't need to be persisted between restarts
last_call_times = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


async def get_anime_info(anilist_id: int):
    query = """
    query ($id: Int) {
        Media (id: $id, type: ANIME) {
            id
            title {
                romaji
                english
                native
            }
            coverImage {
                large
            }
        }
    }
    """

    variables = {"id": anilist_id}

    async with aiohttp.ClientSession() as session:
        async with session.post(ANILIST_API_URL, json={"query": query, "variables": variables}) as response:
            if response.status == 200:
                data = await response.json()
                media = data.get("data", {}).get("Media", {})
                title = media.get("title", {})
                cover_image = media.get("coverImage", {})
                return {
                    "title": title.get("english")
                    or title.get("romaji")
                    or title.get("native")
                    or f"Anilist ID {anilist_id}",
                    "cover_image_url": cover_image.get("large"),
                }
            else:
                return {"title": f"Anilist ID {anilist_id}", "cover_image_url": None}


async def fetch_and_save_snapshot(anilist_id: int, db: AsyncSession):
    try:
        # Check if a snapshot already exists for this Anilist ID
        existing_snapshot = await db.execute(
            select(Snapshot)
            .filter(Snapshot.anilist_id == anilist_id)
            .order_by(desc(Snapshot.timestamp))
            .limit(1)
        )
        existing_snapshot = existing_snapshot.scalar_one_or_none()

        entry = await rest_client.get_entry(anilist_id)
        if entry:
            anime_info = await get_anime_info(anilist_id)

            entry_json = json.dumps(entry, sort_keys=True)

            if existing_snapshot and existing_snapshot.data == entry_json:
                print(f"No changes for Anilist ID {anilist_id}. Skipping snapshot creation.")
                return True

            new_snapshot = Snapshot(
                anilist_id=anilist_id,
                timestamp=datetime.now(timezone.utc),
                data=entry_json,
                anime_title=anime_info["title"],
                cover_image_url=anime_info["cover_image_url"],
            )
            db.add(new_snapshot)
            await db.commit()
            print(f"New snapshot saved for {anime_info['title']} (Anilist ID {anilist_id})")
            return True
        else:
            print(f"No entry found for Anilist ID {anilist_id}")
            return False
    except Exception as e:
        print(f"Error fetching entry for Anilist ID {anilist_id}: {str(e)}")
        await db.rollback()
        return False


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "message": "SeaDexRSS API is running",
        "endpoints": {"/": "This help message", "/{anilist_id}": "Get RSS feed for a specific Anilist ID"},
        "usage": {
            "description": "To use this API, make a GET request to /{anilist_id} where {anilist_id} is the Anilist ID of the anime you want to track.",
            "example": "/12345",
            "response_type": "application/rss+xml",
        },
        "update_interval": f"{UPDATE_INTERVAL.total_seconds() / 60} minutes",
    }


@app.get("/{anilist_id}")
async def get_rss(anilist_id: int, db: AsyncSession = Depends(get_db)):
    current_time = datetime.now(timezone.utc)

    # Check if we need to update based on the last call time
    if anilist_id not in last_call_times or (current_time - last_call_times[anilist_id]) > UPDATE_INTERVAL:
        # Fetch and save a new snapshot
        updated = await fetch_and_save_snapshot(anilist_id, db)
        if not updated:
            # If update failed, and we have no previous data, raise an exception
            if anilist_id not in last_call_times:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data available for Anilist ID {anilist_id}. The entry might not exist or "
                    f"there might be an issue with the Seadex API.",
                )

    # Update the last call time
    last_call_times[anilist_id] = current_time

    # Fetch the last 10 snapshots
    snapshots = await db.execute(
        select(Snapshot)
        .filter(Snapshot.anilist_id == anilist_id)
        .order_by(desc(Snapshot.timestamp))
        .limit(10)
    )
    snapshots = snapshots.scalars().all()

    if not snapshots:
        raise HTTPException(status_code=404, detail=f"No snapshots available for Anilist ID {anilist_id}.")

    rss_feed = generate_rss(snapshots, anilist_id)
    return Response(content=rss_feed, media_type="application/rss+xml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
