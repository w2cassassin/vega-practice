
## Excel

### `/update/`
- **Описание**: Обновляет данные в таблице на основе словаря, где ключи являются закладками из таблицы.
- **Допустимые входные данные**:
  
  file: "<binary>"  // Excel файл  
    ```json
  {  
        "zakladka1": [["значение1", "значение2"], ["значение3"]],  
        "zakladka2": "значение4"  
  }


### `/get_as_json/`
- **Описание**: Получение данных из таблицы в формате JSON.
- **Допустимые входные данные**:
  
  file: "<binary>"  // Excel файл  
    ```json
    {
  "sheet_name": "НазваниеЛиста"  // необязательный параметр  
  "range": "A1:B10"  // необязательный параметр
    }
- **Формат ответа**:
    ```json
    {
        "Лист1":{
            "cells": {
            "A1": {
                "value": "значение",
                "format": {
                    "fontname": "Russia",
                    "fontsize": 20,
                    "fillcolor": "D1F3FF",
                    "textcolor": "D1F3FF",
                    "bold": true,
                    "italic": true,
                    "underline": true,
                    "strikethrough": true,
                    "align": "center",
                    "valign": "center"
                    }
                }
            }
        }
        "merged": ["A1:B2"]
    }


### `/update_from_json/`
- **Описание**: Обновление ячеек таблицы на основе данных в формате JSON.
- **Допустимые входные данные**:
  
  file: "<binary>"  // Excel файл  
    ```json
    {
        "Лист1":{
            "cells": {
            "A1": {
                "value": "значение",
                "format": {
                    "fontname": "Russia",
                    "fontsize": 20,
                    "fillcolor": "D1F3FF",
                    "textcolor": "D1F3FF",
                    "bold": true,
                    "italic": true,
                    "underline": true,
                    "strikethrough": true,
                    "align": "center",
                    "valign": "center"
                    }
                }
            }
        }
        "merged": ["A1:B2"]
    }


### `/update_with_blocks/`
- **Описание**: Обновление блоков таблицы с возможностью объединения ячеек и форматирования.
- **Допустимые входные данные**:
  
  file: "<binary>"  // Excel файл  
    ```json
    {
        "blocks": [  
            {  
            "B2": "значение",  
            "B3": "значение",  
            "C1": "значение"  
            }  
        ],  
        "merged": [  
            "A1:B2",  // Объединение ячеек  
            "C1:C3"  
        ],  
        "format": {
                "fontname": "Russia",
                "fontsize": 20,
                "fillcolor": "D1F3FF",
                "textcolor": "D1F3FF",
                "bold": true,
                "italic": true,
                "underline": true,
                "strikethrough": true,
                "align": "center",
                "valign": "center"
        }
    }

