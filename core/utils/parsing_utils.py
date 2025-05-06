from typing import List, Union, Optional


def parse_csv_value(value_str: str, separator: str = ",") -> List[str]:
    """Парсит строковое значение, разделенное запятыми, в список"""
    if not value_str:
        return []
    return [item.strip() for item in value_str.split(separator) if item.strip()]


def parse_pair_number(pair_slot: Union[str, int]) -> Optional[int]:
    """
    Преобразует номер пары из разных форматов в целое число
    """
    try:
        if isinstance(pair_slot, int):
            return pair_slot

        if isinstance(pair_slot, str):
            if pair_slot.startswith("Пара "):
                return int(pair_slot.replace("Пара ", ""))
            return int(pair_slot)
    except (ValueError, TypeError):
        return None
