
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from utils.metadata import fetch_og_tags

router = APIRouter(
    prefix="/utils",
    tags=["utils"]
)

class MetadataRequest(BaseModel):
    url: HttpUrl

@router.post("/metadata")
async def get_metadata(request: MetadataRequest):
    """Fetch OpenGraph metadata for a URL."""
    try:
        data = await fetch_og_tags(str(request.url))
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
