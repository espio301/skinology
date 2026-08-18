"""
Base spider class and spider registry.

Every retailer spider inherits from ``BaseSpider`` and is registered in
``SPIDER_REGISTRY`` so Celery tasks can iterate over all available spiders
without hard-coding imports.
"""

from .base import BaseSpider
from .the_ordinary import TheOrdinarySpider
from .sephora import SephoraSpider
from .ulta import UltaSpider
from .oliveyoung import OliveYoungSpider

SPIDER_REGISTRY: dict[str, type[BaseSpider]] = {
    "The Ordinary": TheOrdinarySpider,
    "Sephora": SephoraSpider,
    "Ulta": UltaSpider,
    "Olive Young": OliveYoungSpider,
}

__all__ = [
    "BaseSpider",
    "TheOrdinarySpider",
    "SephoraSpider",
    "UltaSpider",
    "OliveYoungSpider",
    "SPIDER_REGISTRY",
]
