#!/usr/bin/env python3
"""운영 요청 DB 트리맵 대시보드 빌더.

Notion API에서 데이터를 가져와 docs/index.html 을 생성합니다.
GitHub Actions 스케줄에서 10분마다 실행됩니다.

Env:
  NOTION_TOKEN  - Notion Integration Internal Token (필수)
  DATABASE_ID   - 선택. 기본값은 운영 요청 DB ID.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID", "68207e6f-61bf-4245-bb2e-c6b204a616a4")
API_VERSION = "2022-06-28"

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "template.html"
OUTPUT_PATH = ROOT / "docs" / "index.html"


def query_database(database_id: str) -> list[dict]:
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": API_VERSION,
        "Content-Type": "application/json",
    }
    results: list[dict] = []
    start_cursor: str | None = None
    while True:
        body: dict = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")
    return results


def get_prop(page: dict, name: str):
    prop = page.get("properties", {}).get(name)
    if not prop:
        return None
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if t == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    if t == "multi_select":
        return [x.get("name") for x in prop.get("multi_select", [])]
    if t == "number":
        return prop.get("number")
    if t == "status":
        st = prop.get("status")
        return st.get("name") if st else None
    if t == "date":
        d = prop.get("date")
        return (d or {}).get("start")
    if t == "unique_id":
        uid = prop.get("unique_id") or {}
        prefix = uid.get("prefix")
        number = uid.get("number")
        if number is None:
            return None
        return f"{prefix}-{number}" if prefix else str(number)
    if t == "people":
        return [x.get("name") for x in prop.get("people", []) if x.get("name")]
    if t == "formula":
        f = prop.get("formula", {})
        return f.get(f.get("type"))
    return None


def transform(pages: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for p in pages:
        title = (get_prop(p, "요청 제목") or "").strip() or "(제목 없음)"
        rid = get_prop(p, "요청 ID")
        modules = get_prop(p, "관련 모듈") or []
        primary = modules[0] if modules else "기타"
        rice = get_prop(p, "RICE 점수")
        p_level = get_prop(p, "P단계") or "-"
        prio = get_prop(p, "우선순위") or "-"
        status = get_prop(p, "처리 상태") or "-"
        cat = get_prop(p, "분류") or "-"
        moscow = get_prop(p, "MoSCoW") or "-"
        owner = get_prop(p, "담당자") or ""
        requester = get_prop(p, "요청자") or ""
        due = get_prop(p, "목표 완료일") or ""
        rows.append({
            "id": str(rid) if rid is not None else "",
            "title": title[:24],
            "full_title": title,
            "module": primary,
            "modules": modules,
            "rice": rice or 0,
            "p": p_level,
            "prio": prio,
            "status": status,
            "cat": cat,
            "moscow": moscow,
            "owner": owner,
            "requester": requester,
            "due": due,
            "url": p.get("url", ""),
        })
    # sort by module (alpha) then rice desc
    rows.sort(key=lambda r: (r["module"], -float(r["rice"] or 0)))
    return rows


def build() -> int:
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN 환경 변수가 없습니다.", file=sys.stderr)
        return 2
    try:
        pages = query_database(DATABASE_ID)
    except urllib.error.HTTPError as e:
        print(f"Notion API HTTP {e.code}: {e.reason}", file=sys.stderr)
        try:
            print(e.read().decode("utf-8"), file=sys.stderr)
        except Exception:
            pass
        return 3
    except Exception as e:
        print(f"Notion API 오류: {e}", file=sys.stderr)
        return 4

    rows = transform(pages)

    kst = timezone(timedelta(hours=9))
    built_at = datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = (
        template
        .replace("__DATA_JSON__", json.dumps(rows, ensure_ascii=False))
        .replace("__BUILT_AT__", built_at)
        .replace("__COUNT__", str(len(rows)))
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"OK — {len(rows)}건 반영, {OUTPUT_PATH.relative_to(ROOT)} 작성 ({built_at})")
    return 0


if __name__ == "__main__":
    sys.exit(build())
