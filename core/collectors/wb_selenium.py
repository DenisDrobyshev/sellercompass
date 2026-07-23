"""Wildberries spider driven by a real Chrome browser (Selenium).

Raw HTTP clients — and even in-page API calls — get IP-throttled by Wildberries
(HTTP 429). The search *page*, however, still renders its product cards. So this
spider does what a person does: it opens Chrome, visits the search page, scrolls
to let the results load, and reads the product cards straight from the page. That
makes it robust to the API throttling that blocks plain HTTP collectors.

Usage:  python -m core.collectors.wb_selenium "чехол для iphone 15"
"""

from __future__ import annotations

import random
import re
import sys
import time
from urllib.parse import quote

from core.config import get_settings
from core.models.product import Product

_HOME = "https://www.wildberries.ru/"
_SEARCH_PAGE = "https://www.wildberries.ru/catalog/0/search.aspx?search={q}"
_CARD = "article.product-card"

_SORT_CHIPS = {"новые", "с фото", "с видео", "по дате", "по популярности", "сначала новые"}
_REVIEW_DIGEST_JS = r"""
const norm = e => (e.textContent || '').replace(/\s+/g, ' ').replace(/Ещё$/, '').trim();
const summary = [...document.querySelectorAll("[class*='generative-feedback__text']")].map(norm);
const chips = [...document.querySelectorAll("[class*='feedbackFiltersChips'] *")].map(norm).filter(Boolean);
return {summary: summary[0] || '', chips: [...new Set(chips)]};
"""

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _human_pause(a: float = 0.7, b: float = 1.8) -> None:
    time.sleep(random.uniform(a, b))


def _int(text: str | None) -> int | None:
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def _price(text: str | None) -> float | None:
    value = _int(text)
    return float(value) if value is not None else None


def _rating(text: str | None) -> float | None:
    match = re.search(r"\d+[.,]\d+|\d+", text or "")
    return float(match.group().replace(",", ".")) if match else None


class WildberriesBrowser:
    """A Selenium-driven Chrome that reads Wildberries like a human visitor."""

    def __init__(self, *, headless: bool | None = None) -> None:
        settings = get_settings()
        self._headless = settings.wb_headless if headless is None else headless
        self._proxy = settings.wb_proxy_url
        self._driver = None

    def __enter__(self) -> "WildberriesBrowser":
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        opts = Options()
        if self._headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1300,900")
        opts.add_argument("--lang=ru-RU")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(f"--user-agent={_UA}")
        if self._proxy:
            opts.add_argument(f"--proxy-server={self._proxy}")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        self._driver = webdriver.Chrome(options=opts)
        self._driver.set_page_load_timeout(45)
        self._driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        return self

    def __exit__(self, *exc: object) -> None:
        if self._driver is not None:
            self._driver.quit()

    def _warm_up(self) -> None:
        self._driver.get(_HOME)
        _human_pause(1.0, 2.2)
        self._driver.execute_script("window.scrollTo(0, 400);")
        _human_pause(0.5, 1.2)

    def _load_results(self, rounds: int = 5) -> None:
        # scroll like a human so the lazy-loaded cards render
        for _ in range(rounds):
            self._driver.execute_script("window.scrollBy(0, 1600);")
            _human_pause(0.7, 1.4)

    def search(self, query: str, *, limit: int = 100) -> list[Product]:
        assert self._driver is not None, "use `with WildberriesBrowser() as wb:`"
        self._warm_up()
        self._driver.get(_SEARCH_PAGE.format(q=quote(query)))
        _human_pause(1.5, 3.0)
        self._load_results()
        cards = self._driver.find_elements("css selector", _CARD)
        products: list[Product] = []
        for card in cards[:limit]:
            product = self._parse_card(card)
            if product is not None:
                products.append(product)
        return products

    def review_digest(self, nm_id: int | str) -> dict:
        """Read Wildberries' own review summary and the aspect facets for a product.

        Raw per-review text is not reliably extractable from the reviews page, but
        WB publishes an aggregated summary and the aspects buyers discuss, and those
        render as plain DOM. Returns ``{"summary": str, "aspects": list[str]}``.
        """
        assert self._driver is not None, "use `with WildberriesBrowser() as wb:`"
        self._warm_up()
        self._driver.get(f"https://www.wildberries.ru/catalog/{nm_id}/feedbacks")
        _human_pause(2.0, 3.5)
        self._load_results(3)
        data = self._driver.execute_script(_REVIEW_DIGEST_JS)
        aspects = [
            chip for chip in data.get("chips", [])
            if 2 < len(chip) < 24 and chip.lower() not in _SORT_CHIPS
        ]
        return {"summary": data.get("summary", ""), "aspects": aspects}

    @staticmethod
    def _parse_card(card) -> Product | None:
        nm = card.get_attribute("data-nm-id")
        if not nm or not nm.isdigit():
            return None

        def cell(selector: str) -> str:
            found = card.find_elements("css selector", selector)
            return found[0].text.strip() if found else ""

        links = card.find_elements("css selector", "a.product-card__link")
        name = links[0].get_attribute("aria-label") if links else ""
        name = name or cell(".product-card__name")
        return Product(
            marketplace="wildberries",
            external_id=int(nm),
            name=name.strip(),
            brand=cell(".product-card__brand") or None,
            price=_price(cell(".price__lower-price")),
            rating=_rating(cell(".address-rate-mini")),
            reviews=_int(cell(".product-card__count")),
            url=f"https://www.wildberries.ru/catalog/{nm}/detail.aspx",
        )


def crawl(query: str, *, limit: int = 100, headless: bool | None = None) -> list[Product]:
    """Open a browser, collect a snapshot for ``query``, and return normalized products."""
    with WildberriesBrowser(headless=headless) as browser:
        return browser.search(query, limit=limit)


def fetch_review_digest(nm_id: int | str, *, headless: bool | None = None) -> dict:
    """Open a browser and return WB's review summary and aspects for a product."""
    with WildberriesBrowser(headless=headless) as browser:
        return browser.review_digest(nm_id)


def _main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "--reviews":
        nm = argv[1] if len(argv) > 1 else ""
        if not nm.isdigit():
            print("usage: python -m core.collectors.wb_selenium --reviews <nmId>")
            return
        digest = fetch_review_digest(nm)
        print(f"[reviews] product {nm}")
        print(f"  aspects buyers discuss: {', '.join(digest['aspects']) or '(none)'}")
        print(f"  WB review summary: {digest['summary'] or '(none)'}")
        return

    from core.engine.demand import validate_demand
    from core.storage.repo import save_snapshot

    query = " ".join(argv) or "чехол для iphone"
    print(f"[spider] opening a browser and crawling Wildberries for {query!r} ...")
    try:
        products = crawl(query)
    except Exception as exc:
        print(f"[spider] browser error: {type(exc).__name__}: {exc}")
        print("[spider] is Google Chrome installed? Selenium Manager fetches the driver, "
              "but Chrome itself must be present.")
        return
    print(f"[spider] collected {len(products)} products")
    if not products:
        print("[spider] no products - WB may have changed its markup, or the page did not load.")
        return
    saved = save_snapshot(query, products)
    print(f"[spider] saved {saved} observations to the database")
    result = validate_demand(query, products)
    print(f"\nStage 2 . Validate demand - {query!r}")
    print(f"  verdict: {'PASS' if result.passed else 'FAIL'}   demand score: {result.score}")
    for reason in result.reasons:
        print(f"   - {reason}")


if __name__ == "__main__":
    _main()
