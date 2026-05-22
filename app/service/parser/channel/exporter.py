"""
Экспорт результатов поиска в Google Sheets (листы Alpha и Сводка) - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
"""

from __future__ import annotations

from datetime import datetime
from typing import List
import time

import gspread
from google.oauth2.service_account import Credentials

from .classifier import VacancyResult
from .config import GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SPREADSHEET_ID

SHEET_ALPHA = "Alpha"
SHEET_SUMMARY = "Сводка"
NUM_COLUMNS = 11

SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)

HEADERS = [
    "В какой канал",
    "Тип",
    "Направление",
    "Компания",
    "Описание (превью)",
    "Ссылка на источник",
    "Оплата",
    "Формат",
    "Дедлайн",
    "Релевантность",
    "Канал-источник",
]

COLUMN_WIDTHS_PX = [126, 105, 112, 154, 420, 280, 84, 84, 98, 105, 126]

DIRECTION_COLORS = {
    "дизайн": {"red": 0.99, "green": 0.89, "blue": 0.93},
    "разработка": {"red": 0.89, "green": 0.95, "blue": 0.99},
    "менеджмент": {"red": 0.91, "green": 0.96, "blue": 0.91},
    "аналитика": {"red": 1.0, "green": 0.95, "blue": 0.88},
    "тестирование": {"red": 0.95, "green": 0.90, "blue": 0.96},
    None: {"red": 0.96, "green": 0.96, "blue": 0.96},
}

HEADER_FORMAT = {
    "backgroundColor": {"red": 0.12, "green": 0.23, "blue": 0.37},
    "textFormat": {
        "bold": True,
        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
        "fontSize": 11,
    },
    "horizontalAlignment": "CENTER",
    "verticalAlignment": "MIDDLE",
    "wrapStrategy": "WRAP",
}

TITLE_FORMAT = {
    "backgroundColor": {"red": 0.12, "green": 0.23, "blue": 0.37},
    "textFormat": {
        "bold": True,
        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
        "fontSize": 14,
    },
    "horizontalAlignment": "CENTER",
    "verticalAlignment": "MIDDLE",
}

LINK_FORMAT = {
    "textFormat": {
        "foregroundColor": {"red": 0.08, "green": 0.40, "blue": 0.75},
        "underline": True,
        "fontSize": 10,
    },
}


def _get_spreadsheet() -> gspread.Spreadsheet:
    if not GOOGLE_SERVICE_ACCOUNT_FILE.is_file():
        raise FileNotFoundError(
            f"Файл service account не найден: {GOOGLE_SERVICE_ACCOUNT_FILE}\n"
            "Создайте ключ в Google Cloud и положите JSON в credentials/"
        )
    creds = Credentials.from_service_account_file(
        str(GOOGLE_SERVICE_ACCOUNT_FILE),
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SPREADSHEET_ID)


def _set_column_widths(worksheet: gspread.Worksheet, widths: list[int]) -> None:
    """Установка ширины колонок одним запросом"""
    requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": idx,
                    "endIndex": idx + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        }
        for idx, width in enumerate(widths)
    ]
    if requests:
        worksheet.client.batch_update(worksheet.spreadsheet_id, {"requests": requests})
        time.sleep(0.1)  # Небольшая пауза после массовой операции


def _get_or_add_worksheet(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    *,
    rows: int = 1000,
    cols: int = NUM_COLUMNS,
) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def _hex_direction_fill(direction: str | None) -> dict:
    return {
        "backgroundColor": DIRECTION_COLORS.get(direction, DIRECTION_COLORS[None]),
        "textFormat": {"fontSize": 10},
        "verticalAlignment": "TOP",
        "wrapStrategy": "WRAP",
    }


def _result_to_row(result: VacancyResult) -> list:
    paid_str = {True: "✅ Оплачивается", False: "🆓 Бесплатно", None: "—"}.get(
        result.is_paid, "—"
    )
    remote_str = {True: "🌐 Удалённо", False: "🏢 Офис", None: "—"}.get(
        result.is_remote, "—"
    )
    publish_labels = {
        "vacancies": "💼 vacancies",
        "project": "🚀 project",
        "as_is": "📚 as_is",
    }
    return [
        publish_labels.get(result.publish_channel, result.publish_channel),
        result.opportunity_type.title(),
        result.direction or "Не определено",
        result.company or "—",
        result.text_preview,
        result.post_url,
        paid_str,
        remote_str,
        result.deadline or "—",
        result.score,
        result.channel,
    ]


def _find_next_row(worksheet: gspread.Worksheet) -> int:
    """Быстрое определение следующей свободной строки"""
    values = worksheet.col_values(1)
    return len(values) + 1 if values else 1


def _ensure_alpha_layout(worksheet: gspread.Worksheet) -> None:
    """Оптимизированная настройка листа Alpha - минимум запросов"""
    try:
        # Проверяем, есть ли уже заголовки
        existing = worksheet.get_all_values()
        if existing and len(existing) >= 2 and existing[1] == HEADERS:
            return

        # Все операции в одном batch_update
        title = f"🔍 Поиск вакансий — {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        # Подготавливаем batch запросы
        requests = []

        # Очистка листа
        requests.append({
            "updateCells": {
                "range": {"sheetId": worksheet.id},
                "fields": "*"
            }
        })

        # Добавляем данные
        body = {
            "requests": requests,
            "includeSpreadsheetInResponse": False
        }

        # Выполняем одной операцией
        worksheet.batch_update(body)

        # Отдельные операции для данных (их немного)
        worksheet.update("A1", [[title]], value_input_option="USER_ENTERED")
        worksheet.update("A2", [HEADERS], value_input_option="USER_ENTERED")
        worksheet.merge_cells("A1:K1")
        worksheet.freeze(rows=2)

        # Форматирование одной операцией
        format_requests = []

        # Формат заголовков
        format_requests.append({
            "repeatCell": {
                "range": {"sheetId": worksheet.id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": TITLE_FORMAT},
                "fields": "userEnteredFormat"
            }
        })

        format_requests.append({
            "repeatCell": {
                "range": {"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": 2},
                "cell": {"userEnteredFormat": HEADER_FORMAT},
                "fields": "userEnteredFormat"
            }
        })

        if format_requests:
            worksheet.batch_update({"requests": format_requests})

        _set_column_widths(worksheet, COLUMN_WIDTHS_PX)

    except Exception as e:
        print(f"⚠️ Ошибка настройки Alpha: {e}")
        raise


def _batch_format_rows(worksheet: gspread.Worksheet, results: List[VacancyResult], start_row: int) -> None:
    """
    КРИТИЧЕСКАЯ ОПТИМИЗАЦИЯ: форматирование ВСЕХ строк одним batch-запросом
    Вместо 50+ запросов - 1 запрос
    """
    if not results:
        return

    # Готовим batch форматы для всех строк
    batch_formats = []
    link_formats = []

    for offset, result in enumerate(results):
        row = start_row + offset
        row_range = f"A{row}:K{row}"

        # Формат всей строки
        batch_formats.append({
            "range": row_range,
            "format": _hex_direction_fill(result.direction)
        })

        # Формат ссылки, если есть
        if result.post_url and result.post_url.startswith("http"):
            link_formats.append({
                "range": f"F{row}",
                "format": LINK_FORMAT
            })

    # Отправляем ВСЕ форматы одним запросом (или несколькими, но с паузой)
    all_formats = batch_formats + link_formats

    # Разбиваем на чанки по 50, чтобы не превысить лимит запроса
    chunk_size = 50
    for i in range(0, len(all_formats), chunk_size):
        chunk = all_formats[i:i+chunk_size]
        if chunk:
            try:
                worksheet.batch_format(chunk)
                if i + chunk_size < len(all_formats):
                    time.sleep(0.05)  # Минимальная пауза между большими чанками
            except Exception as e:
                print(f"⚠️ Ошибка batch-форматирования: {e}")
                # Fallback: применяем по одному, но с паузами
                for fmt in chunk:
                    try:
                        worksheet.format(fmt["range"], fmt["format"])
                        time.sleep(0.02)
                    except:
                        pass


def _write_summary_sheet(
    spreadsheet: gspread.Spreadsheet,
    results: List[VacancyResult],
) -> None:
    """Оптимизированная запись сводки - минимум операций"""
    ws = _get_or_add_worksheet(spreadsheet, SHEET_SUMMARY, rows=20, cols=7)

    summary_headers = [
        "Направление",
        "Всего",
        "Вакансий",
        "Стажировок",
        "Проектов",
        "Удалённых",
        "С оплатой",
    ]
    directions = [
        "дизайн",
        "разработка",
        "менеджмент",
        "аналитика",
        "тестирование",
        None,
    ]

    rows: list[list] = [summary_headers]
    for direction in directions:
        subset = [r for r in results if r.direction == direction]
        label = direction or "Не определено"
        rows.append([
            label,
            len(subset),
            sum(1 for r in subset if r.opportunity_type == "вакансия"),
            sum(1 for r in subset if r.opportunity_type == "стажировка"),
            sum(1 for r in subset if r.opportunity_type == "проект"),
            sum(1 for r in subset if r.is_remote is True),
            sum(1 for r in subset if r.is_paid is True),
        ])

    # Очищаем и записываем данными
    ws.clear()
    ws.update("A1", rows, value_input_option="USER_ENTERED")

    # Форматирование одной операцией
    format_requests = []

    # Заголовки
    format_requests.append({
        "repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                     "startColumnIndex": 0, "endColumnIndex": 7},
            "cell": {"userEnteredFormat": HEADER_FORMAT},
            "fields": "userEnteredFormat"
        }
    })

    # Цветные строки
    for i, direction in enumerate(directions, start=2):
        color = DIRECTION_COLORS.get(direction, DIRECTION_COLORS[None])
        format_requests.append({
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": i-1, "endRowIndex": i,
                         "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {"userEnteredFormat": {"backgroundColor": color}},
                "fields": "userEnteredFormat.backgroundColor"
            }
        })

    if format_requests:
        try:
            ws.batch_update({"requests": format_requests})
        except:
            # Fallback
            for i, direction in enumerate(directions, start=2):
                color = DIRECTION_COLORS.get(direction, DIRECTION_COLORS[None])
                ws.format(f"A{i}:G{i}", {"backgroundColor": color})

    _set_column_widths(ws, [112] * 7)


def export_to_google_sheets(results: List[VacancyResult]) -> str:
    """
    Оптимизированная версия экспорта:
    - Минимум запросов к API
    - Batch-операции вместо последовательных
    - Защита от rate limits
    """
    if not results:
        raise ValueError("Нет данных для экспорта в Google Sheets")

    start_time = time.time()
    print(f"📤 Экспорт {len(results)} вакансий в Google Sheets...")

    # Получаем таблицу
    spreadsheet = _get_spreadsheet()

    # Alpha лист
    alpha = _get_or_add_worksheet(spreadsheet, SHEET_ALPHA)
    _ensure_alpha_layout(alpha)

    # Находим следующую свободную строку
    start_row = _find_next_row(alpha)
    if start_row <= 2:
        start_row = 3

    # Подготовка данных
    data_rows = [_result_to_row(r) for r in results]

    # Запись данных одной операцией append
    alpha.append_rows(data_rows, value_input_option="USER_ENTERED")

    # КРИТИЧЕСКАЯ ОПТИМИЗАЦИЯ: batch-форматирование всех строк
    _batch_format_rows(alpha, results, start_row)

    # Итоговая строка
    summary_row = start_row + len(results)
    alpha.update(
        f"A{summary_row}",
        [[f"📊 Итого найдено: {len(results)}"]],
        value_input_option="USER_ENTERED",
    )

    # Форматирование итоговой строки
    try:
        alpha.format(
            f"A{summary_row}",
            {"textFormat": {"bold": True, "fontSize": 11}}
        )
    except:
        pass

    # Обновляем сводку
    _write_summary_sheet(spreadsheet, results)

    elapsed = time.time() - start_time
    url = spreadsheet.url
    print(f"✅ Google Sheets обновлена за {elapsed:.2f} сек: {url}")

    return url