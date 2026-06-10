from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


EASTERN_TZ = ZoneInfo("America/New_York")
UTC = timezone.utc
PREMARKET_OPEN = time(4, 0)
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
EARLY_REGULAR_CLOSE = time(13, 0)
AFTER_HOURS_CLOSE = time(20, 0)
EARLY_AFTER_HOURS_CLOSE = time(17, 0)


def _observed_day(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    current = date(year, month, 1)
    while current.weekday() != weekday:
        current += timedelta(days=1)
    return current + timedelta(weeks=occurrence - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    current = date(year, month, monthrange(year, month)[1])
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current


def _easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_market_holidays(year: int) -> set[date]:
    easter = _easter_sunday(year)
    return {
        _observed_day(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),
        _nth_weekday(year, 2, 0, 3),
        easter - timedelta(days=2),
        _last_weekday(year, 5, 0),
        _observed_day(date(year, 6, 19)),
        _observed_day(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),
        _nth_weekday(year, 11, 3, 4),
        _observed_day(date(year, 12, 25)),
    }


def get_early_close_days(year: int) -> set[date]:
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    christmas_eve = date(year, 12, 24)
    july_third = date(year, 7, 3)
    early_closes = {thanksgiving + timedelta(days=1)}

    if christmas_eve.weekday() < 5 and christmas_eve not in get_market_holidays(year):
        early_closes.add(christmas_eve)
    if july_third.weekday() < 5 and july_third not in get_market_holidays(year):
        early_closes.add(july_third)

    return early_closes


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in get_market_holidays(day.year)


def is_early_close_day(day: date) -> bool:
    return day in get_early_close_days(day.year)


def _combine(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=EASTERN_TZ).astimezone(UTC)


def get_previous_trading_day(day: date) -> date:
    current = day - timedelta(days=1)
    while not is_trading_day(current):
        current -= timedelta(days=1)
    return current


def get_next_trading_day(day: date) -> date:
    current = day + timedelta(days=1)
    while not is_trading_day(current):
        current += timedelta(days=1)
    return current


def get_market_calendar_context(now: datetime | None = None) -> dict:
    current_utc = now.astimezone(UTC) if now else datetime.now(UTC)
    current_et = current_utc.astimezone(EASTERN_TZ)
    trading_day = current_et.date()
    early_close = is_early_close_day(trading_day)
    trading_day_open = is_trading_day(trading_day)

    regular_close = EARLY_REGULAR_CLOSE if early_close else REGULAR_CLOSE
    after_hours_close = EARLY_AFTER_HOURS_CLOSE if early_close else AFTER_HOURS_CLOSE

    regular_open_at = _combine(trading_day, REGULAR_OPEN)
    regular_close_at = _combine(trading_day, regular_close)
    premarket_open_at = _combine(trading_day, PREMARKET_OPEN)
    after_hours_close_at = _combine(trading_day, after_hours_close)

    session = "closed"
    is_market_open = False
    next_open_at = None
    session_end_at = None

    if trading_day_open:
        if current_utc < premarket_open_at:
            session = "closed"
            next_open_at = premarket_open_at
        elif current_utc < regular_open_at:
            session = "premarket"
            is_market_open = True
            session_end_at = regular_open_at
        elif current_utc < regular_close_at:
            session = "regular"
            is_market_open = True
            session_end_at = regular_close_at
        elif current_utc < after_hours_close_at:
            session = "after_hours"
            is_market_open = True
            session_end_at = after_hours_close_at
        else:
            session = "closed"
            next_open_at = _combine(get_next_trading_day(trading_day), PREMARKET_OPEN)
    else:
        next_open_at = _combine(get_next_trading_day(trading_day), PREMARKET_OPEN)

    previous_trading_day = get_previous_trading_day(trading_day)
    previous_after_hours_close = (
        EARLY_AFTER_HOURS_CLOSE if is_early_close_day(previous_trading_day) else AFTER_HOURS_CLOSE
    )

    if trading_day_open and current_utc >= premarket_open_at:
        last_session_close_at = after_hours_close_at
    else:
        last_session_close_at = _combine(previous_trading_day, previous_after_hours_close)

    return {
        "session": session,
        "is_trading_day": trading_day_open,
        "is_market_open": is_market_open,
        "is_early_close": early_close,
        "trading_date": trading_day,
        "next_open_at": next_open_at,
        "session_end_at": session_end_at,
        "last_session_close_at": last_session_close_at,
        "regular_open_at": regular_open_at if trading_day_open else None,
        "regular_close_at": regular_close_at if trading_day_open else None,
    }


def infer_market_session(event_time: datetime) -> str:
    context = get_market_calendar_context(event_time)
    if not context["is_trading_day"]:
        return "closed"
    return context["session"]


def serialize_market_context(context: dict) -> dict:
    return {
        "session": context["session"],
        "is_trading_day": context["is_trading_day"],
        "is_market_open": context["is_market_open"],
        "is_early_close": context["is_early_close"],
        "trading_date": context["trading_date"],
        "next_open_at": context["next_open_at"],
        "session_end_at": context["session_end_at"],
    }
