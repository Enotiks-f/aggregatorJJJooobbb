"""
Экспорт результатов поиска в Google Sheets (листы Alpha и Сводка).
"""

from __future__ import annotations

from datetime import datetime
from typing import List

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
    worksheet.client.batch_update(worksheet.spreadsheet_id, {"requests": requests})


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
    values = worksheet.col_values(1)
    for idx in range(len(values), 0, -1):
        if values[idx - 1].strip():
            return idx + 1
    return 1


def _ensure_alpha_layout(worksheet: gspread.Worksheet) -> None:
    existing = worksheet.get_all_values()
    if len(existing) >= 2 and existing[1] == HEADERS:
        return

    title = f"🔍 Поиск вакансий — {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    worksheet.clear()
    worksheet.update("A1", [[title]], value_input_option="USER_ENTERED")
    worksheet.update("A2", [HEADERS], value_input_option="USER_ENTERED")
    worksheet.merge_cells("A1:K1")
    worksheet.freeze(rows=2)

    worksheet.format("A1:K1", TITLE_FORMAT)
    worksheet.format("A2:K2", HEADER_FORMAT)
    _set_column_widths(worksheet, COLUMN_WIDTHS_PX)


def _format_data_rows(
    worksheet: gspread.Worksheet,
    results: List[VacancyResult],
    start_row: int,
) -> None:
    for offset, result in enumerate(results):
        row = start_row + offset
        row_range = f"A{row}:K{row}"
        worksheet.format(row_range, _hex_direction_fill(result.direction))
        link_cell = f"F{row}"
        if result.post_url.startswith("http"):
            worksheet.format(link_cell, LINK_FORMAT)


def _write_summary_sheet(
    spreadsheet: gspread.Spreadsheet,
    results: List[VacancyResult],
) -> None:
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

    ws.clear()
    ws.update("A1", rows, value_input_option="USER_ENTERED")
    ws.format("A1:G1", HEADER_FORMAT)

    for i, direction in enumerate(directions, start=2):
        color = DIRECTION_COLORS.get(direction, DIRECTION_COLORS[None])
        ws.format(f"A{i}:G{i}", {"backgroundColor": color, "textFormat": {"fontSize": 10}})

    _set_column_widths(ws, [112] * 7)


def export_to_google_sheets(results: List[VacancyResult]) -> str:
    """
    Добавляет новые строки на лист Alpha и обновляет лист Сводка.
    Возвращает URL таблицы.
    """
    if not results:
        raise ValueError("Нет данных для экспорта в Google Sheets")

    spreadsheet = _get_spreadsheet()
    alpha = _get_or_add_worksheet(spreadsheet, SHEET_ALPHA)
    _ensure_alpha_layout(alpha)

    start_row = _find_next_row(alpha)
    if start_row <= 2:
        start_row = 3

    data_rows = [_result_to_row(r) for r in results]
    alpha.append_rows(data_rows, value_input_option="USER_ENTERED")
    _format_data_rows(alpha, results, start_row)

    summary_row = start_row + len(results)
    alpha.update(
        f"A{summary_row}",
        [[f"Итого найдено: {len(results)}"]],
        value_input_option="USER_ENTERED",
    )
    alpha.format(
        f"A{summary_row}",
        {"textFormat": {"bold": True, "fontSize": 11}},
    )

    _write_summary_sheet(spreadsheet, results)

    url = spreadsheet.url
    print(f"✅ Google Sheets обновлена: {url}")
    return url
