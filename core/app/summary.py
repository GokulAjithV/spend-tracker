"""Summary maths. Pure: no database, no HTTP, no clock - callers pass `today`."""

from datetime import date

from app.schemas import CategorySummary, MomChange, PreviousMonthSummary, Summary, format_paise


def month_range(year: int, month: int) -> tuple[date, date]:
    """Half-open [first of month, first of next month)."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def previous_month(month: date) -> date:
    if month.month == 1:
        return date(month.year - 1, 12, 1)
    return date(month.year, month.month - 1, 1)


def month_label(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def percent_change(current: int, previous: int) -> float | None:
    """(current - previous) / previous * 100, rounded half away from zero to 2 dp.

    Rounded in integers: float maths can land a hair below a .xx5 boundary and
    round the wrong way. The only float is the final, already-rounded value."""
    if previous == 0:
        return None
    scaled = (current - previous) * 100 * 100  # percent in hundredths, times previous
    hundredths, remainder = divmod(abs(scaled), previous)
    if 2 * remainder >= previous:
        hundredths += 1
    return (hundredths if scaled >= 0 else -hundredths) / 100


def is_flagged(current: int, previous: int) -> bool:
    """More than 20% above the previous month: current / previous > 1.2, multiplied out."""
    return previous > 0 and current * 100 > previous * 120


def build_summary(
    month: date, current: dict[str, int], previous: dict[str, int], today: date
) -> Summary:
    start, end = month_range(month.year, month.month)
    current_total = sum(current.values())
    previous_total = sum(previous.values())

    # Name breaks ties so equal totals always come out in the same order.
    categories = sorted(current.keys() | previous.keys(), key=lambda c: (-current.get(c, 0), c))
    by_category = [
        CategorySummary(
            category=c,
            total=format_paise(current.get(c, 0)),
            previous_total=format_paise(previous.get(c, 0)),
            change_percent=percent_change(current.get(c, 0), previous.get(c, 0)),
            flagged=is_flagged(current.get(c, 0), previous.get(c, 0)),
        )
        for c in categories
    ]

    return Summary(
        month=month_label(month),
        is_partial_month=start <= today < end,
        total=format_paise(current_total),
        previous_month=PreviousMonthSummary(
            month=month_label(previous_month(month)), total=format_paise(previous_total)
        ),
        mom_change=MomChange(
            amount=format_paise(current_total - previous_total),
            percent=percent_change(current_total, previous_total),
        ),
        by_category=by_category,
    )
