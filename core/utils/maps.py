COLUMN_MAPS = {
    "1": {5: "title", 6: "lesson_type", 7: "fio", 8: "room"},
    "2": {0: "title", 1: "lesson_type", 2: "fio", 3: "room"},
}

TIME_TO_LESSON = {
    "09:00": 1,
    "10:40": 2,
    "12:40": 3,
    "14:20": 4,
    "16:20": 5,
    "18:00": 6,
    "19:40": 7,
}

# Маппинг дней недели
WEEKDAY_MAP = {
    "Понедельник": 0,
    "Вторник": 1,
    "Среда": 2,
    "Четверг": 3,
    "Пятница": 4,
    "Суббота": 5,
    "Воскресенье": 6,
}

WEEKDAY_MAP_REVERSE = {v: k for k, v in WEEKDAY_MAP.items()}
WEEKDAYS = [k for k in WEEKDAY_MAP.keys()]
