"""Monday-first calendar data; no GUI or third-party calendar dependencies."""

import calendar
from datetime import date


def shift_month(year, month, offset):
    value = year * 12 + month - 1 + offset
    year, index = divmod(value, 12)
    if not 1 <= year <= 9999:
        return None
    return year, index + 1


def move(year, month, action, today=None):
    today = today or date.today()
    if action == 'Today':
        return today.year, today.month
    if action == 'Previous month':
        return shift_month(year, month, -1) or (year, month)
    if action == 'Next month':
        return shift_month(year, month, 1) or (year, month)
    return year, month


def render(year, month, today=None):
    today = today or date.today()
    rows = [f'{calendar.month_name[month]} {year}', '', ' Mon Tue Wed Thu Fri Sat Sun']
    for week in calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(year, month):
        cells = []
        for day in week:
            if not day:
                cells.append('    ')
            elif date(year, month, day) == today:
                cells.append(f'[{day:02d}]')
            else:
                cells.append(f' {day:2d} ')
        rows.append(''.join(cells))
    rows += ['', 'Today is marked [DD].']
    return '\n'.join(rows)
