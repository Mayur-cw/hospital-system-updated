from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Query


@dataclass
class PaginationResult:
    items: list[Any]
    page: int
    per_page: int
    total: int
    total_pages: int
    has_prev: bool
    has_next: bool
    prev_num: int | None
    next_num: int | None

    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        last = 0
        for num in range(1, self.total_pages + 1):
            if (num <= left_edge or
                (self.page - left_current - 1 < num < self.page + right_current) or
                num > self.total_pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def paginate(query: Query, page: int = 1, per_page: int = 20) -> PaginationResult:
    """
    F-12: Standard server-side pagination with clamp limits.
    Default 20 records per page.
    """
    try:
        page = max(1, int(page or 1))
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = max(1, min(100, int(per_page or 20)))
    except (TypeError, ValueError):
        per_page = 20

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()

    return PaginationResult(
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_num=page - 1 if page > 1 else None,
        next_num=page + 1 if page < total_pages else None
    )
