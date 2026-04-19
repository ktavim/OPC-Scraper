from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ScrapeRequest(BaseModel):
    start_url: HttpUrl = Field(..., description="URL to begin the crawl from")
    max_depth: Optional[int] = Field(None, ge=0, description="Override max crawl depth")


class ScrapeResponse(BaseModel):
    start_url: str
    external_hosts: List[dict]
