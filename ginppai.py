#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple
from urllib.request import Request, urlopen


PREFIXES = (
    "https://p.kakaocdn.net/talkp/",
    "https://chat.kakaocdn.net/profile_resource/",
)

TABLE = "cfurl_cache_response"
COL_TIME = "time_stamp"
COL_URL = "request_key"


@dataclass(frozen=True)
class DownloadResult:
    url: str
    ok: bool
    saved_path: Optional[str]
    bytes_written: int
    sha256: Optional[str]
    error: Optional[str]
    elapsed_ms: int
    time_stamp_raw: Optional[str]


def default_cache_db_path() -> Path:
    return (
        Path.home()
        / "Library"
        / "Containers"
        / "com.kakao.KakaoTalkMac"
        / "Data"
        / "Library"
        / "Caches"
        / "Cache.db"
    )


def open_sqlite_readonly(db_path: Path, *, immutable: bool = False, timeout_ms: int = 10_000) -> sqlite3.Connection:
    if not db_path.is_file():
        raise FileNotFoundError(f"DB not found: {db_path}")

    uri = db_path.as_uri() + "?mode=ro"
    if immutable:
        uri += "&immutable=1"

    con = sqlite3.connect(uri, uri=True, timeout=timeout_ms / 1000.0)
    con.execute("PRAGMA query_only=ON;")
    con.execute(f"PRAGMA busy_timeout={int(timeout_ms)};")
    con.row_factory = sqlite3.Row
    return con


def build_sql(limit: Optional[int]) -> Tuple[str, List[object]]:
    where = [
        "(request_key LIKE ? OR request_key LIKE ?)",
        "request_key NOT LIKE '%.jpg?%'",
        "request_key NOT LIKE '%110x110_c.jpg'",
        "request_key NOT LIKE '%.png'",
        "request_key NOT LIKE '%.png?%'",
    ]
    params: List[object] = [PREFIXES[0] + "%", PREFIXES[1] + "%"]

    sql = f"""
        SELECT {COL_URL} AS url, {COL_TIME} AS ts
        FROM "{TABLE}"
        WHERE {" AND ".join(where)}
        ORDER BY {COL_TIME} DESC
    """
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return sql, params


def normalize_ts(ts: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$", ts)
    if not m:
        return "unknown"
    y, mo, d, hh, mm, ss = m.groups()
    return f"{y}{mo}{d}_{hh}{mm}{ss}"


def confirm(msg: str) -> bool:
    while True:
        ans = input(msg).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("y 또는 n으로 입력하세요.")


def build_target_path(out_dir: Path, url: str, ts: str) -> Path:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return out_dir / f"{h}_{normalize_ts(ts)}.jpg"


def fetch_targets_with_retries(
    db_path: Path,
    *,
    limit: Optional[int],
    immutable: bool,
    timeout_ms: int,
    retries: int,
    retry_sleep_ms: int,
) -> List[Tuple[str, str]]:
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            con = open_sqlite_readonly(db_path, immutable=immutable, timeout_ms=timeout_ms)
            try:
                con.execute("BEGIN;")

                sql, params = build_sql(limit)
                rows = con.execute(sql, params).fetchall()

                con.execute("COMMIT;")
            finally:
                con.close()
                
            seen: Set[str] = set()
            targets: List[Tuple[str, str]] = []
            for r in rows:
                url = r["url"]
                ts = r["ts"]
                if url and url not in seen:
                    seen.add(url)
                    targets.append((url, ts))
            return targets

        except sqlite3.OperationalError as e:
            last_err = e
            # database is locked / busy 등. 잠시 기다렸다 재시도.
            if attempt < retries:
                time.sleep(retry_sleep_ms / 1000.0)
                continue
            break
        except Exception as e:
            last_err = e
            break

    raise RuntimeError(f"Failed to read DB after {retries} attempts: {last_err}")


def download_one(
    url: str,
    ts: str,
    out_dir: Path,
    *,
    user_agent: str,
    timeout_sec: float,
    max_bytes: Optional[int],
) -> DownloadResult:
    t0 = time.time()
    target = build_target_path(out_dir, url, ts)
    temp = Path(str(target) + ".part")

    try:
        req = Request(url, headers={"User-Agent": user_agent})
        with urlopen(req, timeout=timeout_sec) as resp:
            h = hashlib.sha256()
            written = 0

            with temp.open("wb") as f:
                while True:
                    chunk = resp.read(1024 * 128)
                    if not chunk:
                        break
                    written += len(chunk)
                    if max_bytes is not None and written > max_bytes:
                        raise RuntimeError("File too large")
                    h.update(chunk)
                    f.write(chunk)

            if target.exists():
                target = target.with_name(target.stem + "_" + h.hexdigest()[:12] + ".jpg")

            os.replace(temp, target)

        return DownloadResult(
            url=url,
            ok=True,
            saved_path=str(target),
            bytes_written=written,
            sha256=h.hexdigest(),
            error=None,
            elapsed_ms=int((time.time() - t0) * 1000),
            time_stamp_raw=ts,
        )

    except Exception as e:
        return DownloadResult(
            url=url,
            ok=False,
            saved_path=None,
            bytes_written=0,
            sha256=None,
            error=str(e),
            elapsed_ms=int((time.time() - t0) * 1000),
            time_stamp_raw=ts,
        )
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--downloads-dir", default="./downloads")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--timeout-sec", type=float, default=15.0)
    ap.add_argument("--max-bytes", type=int, default=50_000_000)
    ap.add_argument("--immutable", action="store_true", help="Not recommended while KakaoTalk is writing")
    ap.add_argument("--sqlite-timeout-ms", type=int, default=10_000)
    ap.add_argument("--db-retries", type=int, default=5)
    ap.add_argument("--db-retry-sleep-ms", type=int, default=300)
    args = ap.parse_args()

    db_path = Path(args.db).expanduser() if args.db else default_cache_db_path()

    try:
        targets = fetch_targets_with_retries(
            db_path,
            limit=args.limit,
            immutable=bool(args.immutable),
            timeout_ms=int(args.sqlite_timeout_ms),
            retries=int(args.db_retries),
            retry_sleep_ms=int(args.db_retry_sleep_ms),
        )
    except Exception as e:
        print(f"[ERROR] DB read failed: {e}", file=sys.stderr)
        return 2

    count = len(targets)
    if count == 0:
        print("다운로드할 파일이 없습니다.")
        return 0

    print(f"{count}개의 파일을 찾았습니다.")
    if not confirm("다운로드할까요? (y/n): "):
        print("취소되었습니다.")
        return 0

    # y 이후에만 폴더 생성
    run_ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.downloads_dir).expanduser() / run_ts
    out_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = None if args.max_bytes <= 0 else int(args.max_bytes)

    ok = fail = 0
    with ThreadPoolExecutor(max_workers=max(1, int(args.concurrency))) as ex:
        futures = [
            ex.submit(
                download_one,
                url, ts, out_dir,
                user_agent="kakao-cfurl-collector/1.0",
                timeout_sec=float(args.timeout_sec),
                max_bytes=max_bytes,
            )
            for url, ts in targets
        ]
        for f in as_completed(futures):
            r = f.result()
            if r.ok:
                ok += 1
                print(r.saved_path)
            else:
                fail += 1
                print(f"[FAIL] {r.url} :: {r.error}", file=sys.stderr)

    print(f"완료: 성공 {ok}, 실패 {fail}")
    print(f"저장 위치: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())