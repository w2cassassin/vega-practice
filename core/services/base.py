from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any, Dict

from fastapi import Form


class BaseDocumentService(ABC):

    def __init__(self):
        self.document = None

    @abstractmethod
    def load(self, file):
        """
        Загружает документ из файла
        """
        pass

    @abstractmethod
    def update(self, params: dict):
        """
        Обновляет документ по переданному словарю
        """
        pass

    @abstractmethod
    def save_to_bytes(self) -> BytesIO:
        """
        Сохраняет документ в байты
        """
        pass

    @abstractmethod
    def save_to_file(self, file_path: str):
        """
        Сохраняет документ в файл
        """
        pass


class BaseConverter(ABC):
    @abstractmethod
    def __call__(self, data: str = Form(...)) -> Dict[str, Any]:
        """
        Базовый класс для конвертеров
        """
        pass
