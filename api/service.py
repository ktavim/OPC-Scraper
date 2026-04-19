import copy
import logging
from typing import Any, Dict

from config_loader import Config
from scraper import Mapper

from .models import ScrapeRequest

logger = logging.getLogger(__name__)


def build_request_config(base: Config, request: ScrapeRequest) -> Config:
    cfg = copy.deepcopy(base)
    cfg.start_url = str(request.start_url)
    if request.max_depth is not None:
        cfg.max_depth = request.max_depth
    return cfg


async def run_scrape(base_config: Config, request: ScrapeRequest) -> Dict[str, Any]:
    config = build_request_config(base_config, request)
    mapper = Mapper(config)
    try:
        await mapper.initialize()
        result = await mapper.map_website()
    finally:
        await mapper.cleanup()

    return {
        "start_url": config.start_url,
        "external_hosts": result.get("external_hosts", []),
    }
