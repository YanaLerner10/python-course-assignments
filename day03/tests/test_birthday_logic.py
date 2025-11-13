import types
from datetime import date
import logic.birthday_logic as bl

# Helper: freeze "today" inside the logic module by swapping its 'date' class
class _FakeDate(date):
    _TODAY = date(2025, 3, 1)
    @classmethod
    def today(cls):
        return cls(cls._TODAY.year, cls._TODAY.month, cls._TODAY.day)

def _set_today(year, month, day):
    _FakeDate._TODAY = date(year, month, day)
    # Replace the 'date' symbol inside the logic module
    bl.date = _FakeDate

def test_same_day_zero():
    _set_today(2025, 3, 1)
    # birthday is today → zero time left
    months, weeks, days = bl.calculate_time_to_birthday(date(2025, 3, 1))
    assert (months, weeks, days) == (0, 0, 0)

def test_future_in_same_year_exact_30_days():
    _set_today(2025, 3, 1)
    # 2025-03-01 → 2025-03-31 = 30 days → 1 month, 0 weeks, 0 days (30-day month approximation)
    months, weeks, days = bl.calculate_time_to_birthday(date(2025, 3, 31))
    assert (months, weeks, days) == (1, 0, 0)

def test_wrap_to_next_year():
    _set_today(2025, 12, 15)
    # Next birthday is 2026-01-10 (since 2025-01-10 already passed)
    # Delta: 26 days → 0 months, 3 weeks, 5 days
    months, weeks, days = bl.calculate_time_to_birthday(date(2025, 1, 10))
    assert (months, weeks, days) == (0, 3, 5)

def test_feb29_on_non_leap_year_current_year():
    _set_today(2025, 2, 28)  # 2025 is not leap
    bday = date(2000, 2, 29)  # use a leap year to make Feb 29 a valid date
    # Rolls to Mar 1 in the same year → 1 day
    assert bl.calculate_time_to_birthday(bday) == (0, 0, 1)

def test_feb29_on_non_leap_year_next_year():
    _set_today(2025, 3, 2)    # 2025 is not leap
    bday = date(2000, 2, 29)  # valid Feb 29
    # Next occurrence is 2026-03-01
    # 2025-03-02 → 2026-03-01 = 364 days → 12m (360), 0w, 4d
    assert bl.calculate_time_to_birthday(bday) == (12, 0, 4)
