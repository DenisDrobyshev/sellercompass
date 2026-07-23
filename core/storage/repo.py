"""Persistence for marketplace observations — save and read back snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from core.models.product import Product
from core.storage.db import get_engine
from core.storage.models import ProductObservation, WatchQuery


def save_snapshot(
    query: str,
    products: list[Product],
    *,
    engine: Engine | None = None,
    collected_at: datetime | None = None,
) -> int:
    """Persist a ranked snapshot of products for a query. Returns rows written."""
    engine = engine or get_engine()
    ts = collected_at or datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add_all(
            ProductObservation(
                marketplace=p.marketplace,
                query=query,
                external_id=p.external_id,
                root_id=p.root_id,
                name=p.name,
                brand=p.brand,
                seller=p.seller,
                price=p.price,
                base_price=p.base_price,
                rating=p.rating,
                reviews=p.reviews,
                position=pos,
                collected_at=ts,
            )
            for pos, p in enumerate(products, start=1)
        )
        session.commit()
    return len(products)


def latest_snapshot(query: str, *, engine: Engine | None = None) -> list[Product]:
    """Return the most recent stored snapshot for a query, ranked by position."""
    engine = engine or get_engine()
    with Session(engine) as session:
        latest = session.scalar(
            select(func.max(ProductObservation.collected_at)).where(
                ProductObservation.query == query
            )
        )
        if latest is None:
            return []
        rows = session.scalars(
            select(ProductObservation)
            .where(
                ProductObservation.query == query,
                ProductObservation.collected_at == latest,
            )
            .order_by(ProductObservation.position)
        ).all()
    return [
        Product(
            marketplace=r.marketplace,
            external_id=r.external_id,
            root_id=r.root_id,
            name=r.name,
            brand=r.brand,
            seller=r.seller,
            price=r.price,
            base_price=r.base_price,
            rating=r.rating,
            reviews=r.reviews,
        )
        for r in rows
    ]


def snapshot_totals_over_time(
    query: str, *, engine: Engine | None = None
) -> list[tuple[datetime, int]]:
    """Return (collected_at, total_reviews) per snapshot, oldest first — for trend."""
    engine = engine or get_engine()
    with Session(engine) as session:
        rows = session.execute(
            select(
                ProductObservation.collected_at,
                func.coalesce(func.sum(ProductObservation.reviews), 0),
            )
            .where(ProductObservation.query == query)
            .group_by(ProductObservation.collected_at)
            .order_by(ProductObservation.collected_at)
        ).all()
    return [(row[0], int(row[1])) for row in rows]


def add_watch(query: str, *, engine: Engine | None = None) -> bool:
    """Add a query to the collection watchlist. Returns False if already present."""
    engine = engine or get_engine()
    with Session(engine) as session:
        if session.scalar(select(WatchQuery).where(WatchQuery.query == query)):
            return False
        session.add(WatchQuery(query=query, added_at=datetime.now(timezone.utc)))
        session.commit()
    return True


def list_watch(*, engine: Engine | None = None) -> list[str]:
    """Return the watched queries, sorted."""
    engine = engine or get_engine()
    with Session(engine) as session:
        return list(session.scalars(select(WatchQuery.query).order_by(WatchQuery.query)))


def remove_watch(query: str, *, engine: Engine | None = None) -> bool:
    """Remove a query from the watchlist. Returns False if it was not present."""
    engine = engine or get_engine()
    with Session(engine) as session:
        obj = session.scalar(select(WatchQuery).where(WatchQuery.query == query))
        if obj is None:
            return False
        session.delete(obj)
        session.commit()
    return True


def overlap_review_totals(
    query: str, *, engine: Engine | None = None
) -> list[tuple[datetime, int]]:
    """Reviews summed over products common to the earliest and latest snapshot.

    Comparing the same products across snapshots removes the noise from crawls
    that capture different product sets, so the demand trend reflects real change
    rather than sampling variance. Returns [] with fewer than two snapshots or no
    overlapping products.
    """
    engine = engine or get_engine()
    with Session(engine) as session:
        times = list(
            session.scalars(
                select(ProductObservation.collected_at)
                .where(ProductObservation.query == query)
                .distinct()
                .order_by(ProductObservation.collected_at)
            )
        )
        if len(times) < 2:
            return []
        first, last = times[0], times[-1]

        def reviews_at(ts: datetime) -> dict[int, int]:
            rows = session.execute(
                select(ProductObservation.external_id, ProductObservation.reviews).where(
                    ProductObservation.query == query,
                    ProductObservation.collected_at == ts,
                )
            ).all()
            return {ext: (rev or 0) for ext, rev in rows}

        early, late = reviews_at(first), reviews_at(last)
        common = set(early) & set(late)
        if not common:
            return []
    return [(first, sum(early[e] for e in common)), (last, sum(late[e] for e in common))]
