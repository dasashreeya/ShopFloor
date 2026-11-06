import pytest

from shopfloor.llm import FakeLLM
from shopfloor.service import ShopFloor
from shopfloor.store import Store


@pytest.fixture
def sf() -> ShopFloor:
    s = ShopFloor(Store(":memory:"), FakeLLM())
    s.crawl()
    return s
