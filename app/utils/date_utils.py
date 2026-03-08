import calendar


def get_last_day_of_month(month: int, year: int) -> int:
    """
    Retrieve the last day of the month
    """
    return calendar.monthrange(year, month)[1]
