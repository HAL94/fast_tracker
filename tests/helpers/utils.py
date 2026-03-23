import calendar
import random
from datetime import date


def generate_random_date(year, month):
    # calendar.monthrange returns (first_day_weekday, number_of_days)
    _, last_day = calendar.monthrange(year, month)

    # Pick a random day between 1 and the last day of that specific month
    random_day = random.randint(1, last_day)

    return date(year, month, random_day)

