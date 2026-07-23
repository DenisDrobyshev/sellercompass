"""Storage round-trip tests using a temporary SQLite file (no network)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine

from core.models.product import Product
from core.storage.models import Base
from core.storage.repo import (
    latest_snapshot,
    overlap_review_totals,
    save_snapshot,
    snapshot_totals_over_time,
)


def _engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return engine


def _p(external_id: int, reviews: int, price: float) -> Product:
    return Product(
        marketplace="wildberries", external_id=external_id, name=f"item {external_id}",
        reviews=reviews, price=price, rating=4.5,
    )


def test_save_and_read_latest(tmp_path):
    engine = _engine(tmp_path)
    save_snapshot("q", [_p(1, 100, 500), _p(2, 50, 700)], engine=engine)
    latest = latest_snapshot("q", engine=engine)
    assert [p.external_id for p in latest] == [1, 2]  # ranked by position
    assert latest[0].reviews == 100


def test_latest_returns_only_newest_snapshot(tmp_path):
    engine = _engine(tmp_path)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = t1 + timedelta(days=1)
    save_snapshot("q", [_p(1, 100, 500)], engine=engine, collected_at=t1)
    save_snapshot("q", [_p(1, 180, 500), _p(2, 20, 400)], engine=engine, collected_at=t2)
    latest = latest_snapshot("q", engine=engine)
    assert len(latest) == 2
    assert latest[0].reviews == 180


def test_totals_over_time(tmp_path):
    engine = _engine(tmp_path)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = t1 + timedelta(days=1)
    save_snapshot("q", [_p(1, 1000, 500)], engine=engine, collected_at=t1)
    save_snapshot("q", [_p(1, 1500, 500)], engine=engine, collected_at=t2)
    totals = snapshot_totals_over_time("q", engine=engine)
    assert [v for _, v in totals] == [1000, 1500]


def test_overlap_review_totals_uses_common_products(tmp_path):
    engine = _engine(tmp_path)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = t1 + timedelta(days=1)
    save_snapshot("q", [_p(1, 100, 500), _p(2, 200, 500)], engine=engine, collected_at=t1)
    save_snapshot("q", [_p(2, 260, 500), _p(3, 999, 500)], engine=engine, collected_at=t2)
    totals = overlap_review_totals("q", engine=engine)
    # only product 2 is common to both snapshots: 200 -> 260 (products 1 and 3 ignored)
    assert [v for _, v in totals] == [200, 260]
