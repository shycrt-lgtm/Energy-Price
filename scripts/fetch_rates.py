#!/usr/bin/env python3
"""삼천리 요금단가표(경기/인천)를 주소 규칙으로 내려받아 inbox/ 에 저장하고 parse_rates.py 로 누적한다.

주소 규칙:
    https://ecpgw.samchully.co.kr/res/files/contents/docs/prices/{연도}/단가변동표_{지역}_{YYYY-MM-DD}_{NN}.{xlsx|xls}

사용법:
    python3 scripts/fetch_rates.py                  # 최근 3개월 ~ 다음 달 1일자 파일 확인
    python3 scripts/fetch_rates.py --since 2026-01  # 지정 월부터 확인(과거 이력 채우기)

- 이미 데이터에 있는 월은 건너뛴다.
- 요금 변동이 없는 달은 파일이 없을 수 있으므로, 404 는 오류로 보지 않는다.
- 파일이 하나도 없으면 아무것도 바꾸지 않고 종료한다.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_rates as P  # noqa: E402

BASE = "https://ecpgw.samchully.co.kr/res/files/contents/docs/prices/{year}/{name}"
REGIONS = ("경기", "인천")
EXTS = ("xlsx", "xls")
SEQS = (1, 2, 3)
MAGIC = {"xlsx": b"PK", "xls": b"\xd0\xcf\x11\xe0"}
INBOX = P.ROOT / "inbox"


def month_starts(since, today):
    """since(첫째 날)부터 다음 달 1일까지의 월 시작일 목록."""
    months, cur = [], since
    end = (today.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    while cur <= end:
        months.append(cur)
        cur = (cur.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    return months


def default_since(today):
    y, m = today.year, today.month - 3
    if m < 1:
        y, m = y - 1, m + 12
    return dt.date(y, m, 1)


def fetch(url):
    """(상태코드, 본문) 반환. 파일이 없거나 거부돼도 예외 없이 상태코드만 돌려준다."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://cs.samchully.co.kr/",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return f"접속오류({type(e).__name__})", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM")
    args = ap.parse_args()
    today = dt.date.today()
    since = dt.datetime.strptime(args.since, "%Y-%m").date() if args.since else default_since(today)

    store = P.load()
    have = {r: set(store["regions"].get(r, {}).get("months", {})) for r in REGIONS}
    INBOX.mkdir(exist_ok=True)
    saved = []
    stats = {}
    for region in REGIONS:
        for month in month_starts(since, today):
            iso = month.isoformat()
            if iso in have[region]:
                continue
            for seq in SEQS:
                for ext in EXTS:
                    name = f"단가변동표_{region}_{iso}_{seq:02d}.{ext}"
                    url = BASE.format(year=month.year, name=urllib.parse.quote(name))
                    status, data = fetch(url)
                    stats[status] = stats.get(status, 0) + 1
                    if sum(stats.values()) <= 6:
                        print(f"  요청 {status}: {name}")
                    time.sleep(0.5)
                    if data and data.startswith(MAGIC[ext]):
                        path = INBOX / name
                        path.write_bytes(data)
                        saved.append(path)
                        print("받음:", name, len(data), "bytes")
                        break
    print("응답 코드 집계:", stats)
    if not saved:
        print("새 파일 없음")
        return
    P.main([str(p) for p in sorted(saved)])


if __name__ == "__main__":
    main()
