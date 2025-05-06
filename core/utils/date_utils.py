import datetime
import calendar
from typing import Dict, List, Optional, Tuple, Union
from dateutil import parser


def get_pair_time(pair_number: int) -> Tuple[str, str]:
    """Возвращает время начала и окончания пары по её номеру"""
    pair_times = {
        1: ("9:00", "10:30"),
        2: ("10:40", "12:10"),
        3: ("12:40", "14:10"),
        4: ("14:20", "15:50"),
        5: ("16:20", "17:50"),
        6: ("18:00", "19:30"),
        7: ("19:40", "21:10"),
    }
    return pair_times.get(pair_number, ("00:00", "00:00"))


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Парсит дату из строки формата YYYY-MM-DD"""
    try:
        return parser.parse(date_str).date()
    except Exception:
        return None


def get_pair_number_from_time(time_slot: str) -> Optional[int]:
    """
    Определяет номер пары по времени начала
    """
    start_time = time_slot.split(" - ")[0].strip() if " - " in time_slot else None

    if not start_time:
        return None

    for pair in range(1, 8):
        pair_start, _ = get_pair_time(pair)
        if start_time == pair_start:
            return pair

    return None


def get_current_semcode() -> int:
    """Получает текущий семкод на основе текущей даты"""
    today = datetime.date.today()
    year = today.year
    month = today.month

    if 2 <= month <= 6:
        return year * 10 + 2
    elif month >= 9 or month == 1:
        if month == 1:
            return (year - 1) * 10 + 1
        return year * 10 + 1
    else:
        return year * 10 + 1


def calculate_semester_dates(semcode: int) -> Tuple[datetime.date, datetime.date]:
    """Рассчитывает даты начала и конца семестра на основе семкода"""
    year = semcode // 10
    semester = semcode % 10

    if semester == 1:
        sept_first = datetime.date(year, 9, 1)
        days_ahead = 0 - sept_first.weekday()
        if days_ahead < 0:
            days_ahead += 7
        semester_start = sept_first + datetime.timedelta(days=days_ahead)
    else:
        feb_first = datetime.date(year, 2, 1)
        days_ahead = 0 - feb_first.weekday()
        if days_ahead < 0:
            days_ahead += 7
        semester_start = feb_first + datetime.timedelta(days=days_ahead + 7)

    semester_end = semester_start + datetime.timedelta(weeks=18, days=-1)

    return semester_start, semester_end


def generate_semester_days(semcode: int) -> List[Dict[str, Union[int, datetime.date]]]:
    """Генерирует список всех дней семестра с информацией о неделе и дне недели"""
    semester_start, _ = calculate_semester_dates(semcode)

    days = []
    for week in range(1, 19):
        for weekday in range(7):
            current_date = semester_start + datetime.timedelta(
                weeks=week - 1, days=weekday
            )
            days.append(
                {
                    "semcode": semcode,
                    "day": current_date,
                    "weekday": weekday,
                    "week": week,
                }
            )

    return days
