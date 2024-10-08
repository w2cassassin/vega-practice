import json
from typing import Any, Dict

from fastapi import Form, HTTPException, status
from lxml import etree
from pydantic import ValidationError

from core.services.base import BaseConverter


class JSONConverter(BaseConverter):
    def __call__(self, data: str = Form(...)) -> Dict[str, Any]:
        """
        Преобразованрие JSON в словарь
        """
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise HTTPException(
                detail={"error": "Неверный формат JSON"},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class XMLConverter(BaseConverter):
    def __call__(self, data: str = Form(...)) -> Dict[str, Any]:
        """
        Преобразованрие XML в словарь
        """
        try:
            root = etree.fromstring(data)
            xml_dict = {}
            for child in root:
                xml_dict[child.tag] = child.text
            return xml_dict
        except etree.XMLSyntaxError as e:
            raise HTTPException(
                detail={"error": "Неверный формат XML"},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class DataConverter(BaseConverter):
    def __call__(self, data: str = Form(...)) -> Dict[str, Any]:
        """
        Автоматический выбор конвертора для входной строки
        """
        if data.strip().startswith("{"):
            return JSONConverter()(data)
        else:
            return XMLConverter()(data)
