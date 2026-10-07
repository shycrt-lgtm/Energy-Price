#!/usr/bin/env python3
"""삼천리 도시가스 요금단가표(.xls, 경기/인천)를 읽어 data/rates.json · data/rates.js 에 누적한다.

사용법:
    python3 scripts/parse_rates.py inbox/*.xls

- 파일 1개 = 시트 1개(시트명 '경기' 또는 '인천'). .xls / .xlsx 모두 지원.
- 파일 안에 전월(A)·당월(B) 단가가 모두 있으므로, 새 파일 1개로 두 달치가 채워진다.
- 같은 월을 다시 넣으면 당월(B) 값이 우선하고, 전월(A) 값은 비어 있는 경우에만 채운다.
"""
import json
import re
import sys
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "data" / "rates.json"
DATA_JS = ROOT / "data" / "rates.js"
UNIT = "원/MJ (VAT 별도)"


def squash(text: str) -> str:
    """공백·줄바꿈 제거 (취 사 용 -> 취사용)."""
    return re.sub(r"\s+", "", str(text or ""))


def collapse(text: str) -> str:
    """연속 공백만 하나로 정리."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def to_iso(label: str) -> str:
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", str(label))
    if not m:
        raise ValueError(f"단가변동일을 찾을 수 없음: {label!r}")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def num(value):
    if value in ("", None):
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


class XlsxSheet:
    """openpyxl 시트를 xlrd 시트와 같은 인터페이스(name, nrows, row_values)로 감싼다."""

    def __init__(self, ws):
        self.name = ws.title
        self._rows = [["" if c is None else c for c in row] for row in ws.iter_rows(values_only=True)]
        self.nrows = len(self._rows)

    def row_values(self, r):
        row = self._rows[r]
        return row + [""] * (12 - len(row))


def open_sheet(path):
    """.xls / .xlsx 파일의 첫 시트를 연다."""
    if str(path).lower().endswith(".xlsx"):
        import openpyxl

        return XlsxSheet(openpyxl.load_workbook(path, data_only=True).worksheets[0])
    return xlrd.open_workbook(path).sheet_by_index(0)


def find_header(sheet):
    """'A) 2026.09.01' / 'B) 2026.10.01' 이 있는 행과 열 위치를 찾는다."""
    for r in range(min(sheet.nrows, 12)):
        values = sheet.row_values(r)
        cols = {}
        for c, cell in enumerate(values):
            m = re.match(r"\s*([AB])\)", str(cell))
            if m:
                cols[m.group(1)] = c
        if len(cols) == 2:
            return r, cols["A"], cols["B"], values
    raise ValueError("헤더(A)/B) 단가변동일)를 찾을 수 없음")


def parse_sheet(sheet):
    """시트 하나 -> (월 A, 월 B, 행 목록, 비고)."""
    header_row, col_a, col_b, header = find_header(sheet)
    date_a = to_iso(header[col_a])
    date_b = to_iso(header[col_b])
    col_remark = col_b + 2

    rows = []
    note = ""
    c1 = c2 = parent3 = ""
    for r in range(header_row + 1, sheet.nrows):
        v = sheet.row_values(r)
        label1 = str(v[1]).strip()
        if label1.startswith("▷"):
            note = collapse(label1.lstrip("▷"))
            break
        if label1:
            c1 = squash(label1)
            c2 = ""
            parent3 = ""
        label2 = str(v[2]).strip()
        if label2:
            c2 = squash(label2)
            parent3 = ""
        label3 = collapse(v[3])
        if label3.startswith("-"):
            c3 = f"{parent3} {collapse(label3.lstrip('- '))}".strip()
        else:
            c3 = label3
            parent3 = label3
        price_a, price_b = num(v[col_a]), num(v[col_b])
        if price_a is None and price_b is None:
            continue
        key = " > ".join(p for p in (c1, c2, c3) if p)
        remark = collapse(v[col_remark])
        rows.append({"key": key, "group": c1, "a": price_a, "b": price_b, "remark": remark})
    return date_a, date_b, rows, note


def load():
    if DATA_JSON.exists():
        return json.loads(DATA_JSON.read_text(encoding="utf-8"))
    return {"unit": UNIT, "regions": {}}


def merge(store, region, date_a, date_b, rows, note):
    reg = store["regions"].setdefault(region, {"order": [], "months": {}, "remarks": {}, "note": ""})
    for row in rows:
        if row["key"] not in reg["order"]:
            reg["order"].append(row["key"])
        if row["remark"]:
            reg["remarks"][row["key"]] = row["remark"]
        if row["a"] is not None:
            reg["months"].setdefault(date_a, {}).setdefault(row["key"], row["a"])
        if row["b"] is not None:
            reg["months"].setdefault(date_b, {})[row["key"]] = row["b"]
    if note:
        reg["note"] = note
    reg["months"] = dict(sorted(reg["months"].items()))


def main(paths):
    if not paths:
        sys.exit(__doc__)
    store = load()
    for p in paths:
        sheet = open_sheet(p)
        region = sheet.name.strip()
        date_a, date_b, rows, note = parse_sheet(sheet)
        merge(store, region, date_a, date_b, rows, note)
        print(f"{Path(p).name}: {region} {date_a} -> {date_b}, {len(rows)}개 용도")
    store["months"] = sorted({m for reg in store["regions"].values() for m in reg["months"]})
    DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    DATA_JSON.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    DATA_JS.write_text("window.RATES = " + json.dumps(store, ensure_ascii=False) + ";\n", encoding="utf-8")
    print("저장:", DATA_JSON, DATA_JS)


if __name__ == "__main__":
    main(sys.argv[1:])
