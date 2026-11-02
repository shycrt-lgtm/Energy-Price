#!/usr/bin/env python3
"""한국가스공사 '발전용 천연가스 요금' 페이지에서 당월 요금(일반발전사업자)을 읽어 data/kogas.json·kogas.js 에 누적한다.

페이지: https://www.kogas.or.kr/site/koGas/1040402000000
- 페이지에는 당월(시행일 YYYY. M. 1 ~ 말일) 요금표 하나만 게시된다.
- 표 열: 일반발전사업자 / 집단에너지사업자, 행: 원료비 / 공급비 / 합계 (원/GJ)
- 일반발전사업자 열(첫 번째 숫자)을 사용한다.

안전장치:
- 시행월을 찾지 못하거나, 원료비+공급비가 합계와 맞지 않으면 아무것도 바꾸지 않는다.
- 이미 같은 월 값이 있고 숫자가 같으면 건너뛴다. 값이 다르면(정정 고시) 새 값으로 덮어쓴다.

사용법:
    python3 scripts/fetch_kogas.py              # 페이지에서 수집
    python3 scripts/fetch_kogas.py --html FILE  # 저장된 HTML로 시험
"""
import argparse
import html as htmllib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "kogas.json"
JS_PATH = ROOT / "data" / "kogas.js"
URL = "https://www.kogas.or.kr/site/koGas/1040402000000"

NUM = r"(\d{1,3}(?:,\d{3})*\.\d+|\d+\.\d+)"
GAP = r"[^\d]{0,80}?"


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "ko-KR,ko;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", "replace")


def to_text(page):
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    page = htmllib.unescape(page)
    return re.sub(r"\s+", " ", page)


def num(s):
    return float(s.replace(",", ""))


def find_month(text):
    """'시행일' 뒤 첫 날짜(YYYY. M. D / YYYY-MM-DD / YYYY년 M월 D일) → 'YYYY-MM'."""
    date = r"(20\d{2})\s*(?:\.|-|년)\s*(\d{1,2})\s*(?:\.|-|월)\s*(\d{1,2})"
    for m in re.finditer(r"시행", text):
        d = re.search(date, text[m.end(): m.end() + 80])
        if d:
            y, mo = int(d.group(1)), int(d.group(2))
            if 1 <= mo <= 12:
                return f"{y:04d}-{mo:02d}"
    return None


def find_row(text, label):
    """라벨 뒤에 오는 두 숫자(일반발전, 집단에너지) 후보들을 모두 돌려준다."""
    pat = re.compile(label + GAP + NUM + r"[^\d]{0,30}?" + NUM)
    return [(num(m.group(1)), num(m.group(2)), m.start()) for m in pat.finditer(text)]


def parse(page):
    text = to_text(page)
    month = find_month(text)
    if not month:
        raise ValueError("시행월을 찾지 못함")
    fuels, supplies, totals = find_row(text, "원료비"), find_row(text, "공급비"), find_row(text, r"합\s*계")
    for f in fuels:
        for s in supplies:
            if s[2] <= f[2]:
                continue
            for t in totals:
                if t[2] <= s[2]:
                    continue
                if abs(f[0] + s[0] - t[0]) < 0.02:
                    return month, {"fuel": f[0], "supply": s[0], "total": round(t[0], 2)}, \
                        {"fuel": f[1], "supply": s[1], "total": round(t[1], 2)}
    raise ValueError(f"요금표 숫자를 찾지 못함(원료비 {len(fuels)}·공급비 {len(supplies)}·합계 {len(totals)} 후보)")


def save(store):
    JSON_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    JS_PATH.write_text("window.KOGAS = " + json.dumps(store, ensure_ascii=False) + ";\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="저장된 HTML 파일로 시험")
    args = ap.parse_args()

    if args.html:
        page = Path(args.html).read_text(encoding="utf-8", errors="replace")
    else:
        try:
            page = fetch(URL)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"KOGAS 페이지 접속 실패: {type(e).__name__}: {e}")
            sys.exit(1)

    try:
        month, gen, chp = parse(page)
    except ValueError as e:
        print("KOGAS 요금 파싱 실패:", e)
        print("본문 일부:", to_text(page)[:1500])
        sys.exit(1)

    print(f"KOGAS {month} 일반발전 {gen} / 집단에너지 {chp}")
    store = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    months = store.setdefault("months", {})
    if months.get(month) == gen:
        print("변경 없음(이미 반영된 월)")
        return
    if month in months:
        print(f"{month} 값 정정: {months[month]} → {gen}")
    months[month] = gen
    store["months"] = dict(sorted(months.items()))
    save(store)
    print(f"{month} 반영 완료")


if __name__ == "__main__":
    main()
