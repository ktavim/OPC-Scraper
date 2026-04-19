import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

from config_loader import load_config

from .models import ScrapeRequest, ScrapeResponse
from .service import run_scrape

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_path = os.environ.get("SCRAPER_CONFIG_PATH", "/etc/scraper/config.json")
    app.state.base_config = load_config(config_path)
    max_parallel = int(os.environ.get("SCRAPER_MAX_PARALLEL", "2"))
    app.state.semaphore = asyncio.Semaphore(max_parallel)
    logger.info("Loaded base config from %s (max_parallel=%d)", config_path, max_parallel)
    yield


app = FastAPI(
    title="Hosts Scraper API",
    description="Submit a start_url to crawl a site and collect external hosts.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest, http_request: Request) -> ScrapeResponse:
    base_config = http_request.app.state.base_config
    semaphore: asyncio.Semaphore = http_request.app.state.semaphore

    async with semaphore:
        try:
            result = await run_scrape(base_config, request)
        except Exception as e:
            logger.exception("Scrape failed for %s", request.start_url)
            raise HTTPException(status_code=500, detail=f"Scrape failed: {e.__class__.__name__}")

    return ScrapeResponse(**result)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
