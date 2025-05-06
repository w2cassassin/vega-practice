from io import BytesIO
from typing import Dict

from core.services.converters.excel_converter import ExcelConverter
from core.services.converters.ics_converter import ICSConverter
from core.schemas.schedule import ScheduleResult


class StandardContentConverter:
    """Конвертирует файлы в стандартный формат с расписанием по неделям"""

    def __init__(self):
        self.excel_converter = ExcelConverter()
        self.ics_converter = ICSConverter()
        self.supported_formats = {"xlsx": self._convert_excel, "ics": self._convert_ics}

    def convert(self, file_data: bytes, file_format: str) -> ScheduleResult:
        """
        Конвертировать файл в стандартный формат
        """
        if file_format not in self.supported_formats:
            raise ValueError(f"Неподдерживаемый формат файла: {file_format}")

        return self.supported_formats[file_format](file_data)

    def _convert_excel(self, file_data: bytes) -> ScheduleResult:
        """Конвертировать Excel файл в стандартный формат"""
        return self.excel_converter.convert(file_data)

    def _convert_ics(self, file_data: bytes) -> ScheduleResult:
        """Конвертировать ICS файл в стандартный формат"""
        return self.ics_converter.convert(file_data)
