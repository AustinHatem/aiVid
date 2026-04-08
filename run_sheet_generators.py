import glob
import subprocess
from datetime import datetime

import gspread

SHEET_ID = "1h1pPMEshYzfCyqA-xc4NHVcGotQk_-S_LzfFhPaPlhQ"
REPO_DIR = "/opt/data/aiVid-main"
SERVICE_ACCOUNT_GLOB = "/opt/data/aiVid-main/*-firebase-adminsdk-*.json"
MAX_GENERATE_COUNT = 10
DATA_START_ROW = 4
DEFAULT_BG_COLOR = {"red": 1, "green": 1, "blue": 1}
HIGHLIGHT_BG_COLOR = {"red": 0.85, "green": 0.94, "blue": 0.83}

WORKSHEETS = {
    "USA Male Ads": {"mode": "loop", "command": ["python3", "generate_v2.py"], "columns": "G"},
    "Latam Female Ads": {"mode": "loop", "command": ["python3", "generate_v3.py"], "columns": "G"},
    "V4 Ads": {"mode": "batch", "command": ["python3", "generate_v4.py"], "columns": "E"},
    "V5 Ads": {"mode": "loop", "command": ["python3", "generate_v5.py"], "columns": "F"},
}


def parse_count(value: str) -> int:
    value = (value or "").strip()
    if not value:
        return 0
    try:
        n = int(value)
        return min(max(n, 0), MAX_GENERATE_COUNT)
    except ValueError:
        raise ValueError(f"Invalid count in B1: {value!r}")


def run_command(command):
    return subprocess.run(
        command,
        cwd=REPO_DIR,
        text=True,
        capture_output=True,
        check=False,
    )


def last_nonempty_row(ws) -> int:
    return len(ws.get_all_values())


def set_row_background(ws, start_row: int, end_row: int, end_col: str, color: dict):
    if start_row > end_row:
        return
    ws.format(f"A{start_row}:{end_col}{end_row}", {"backgroundColor": color})


def refresh_new_row_highlight(ws, end_col: str, previous_last_row: int, current_last_row: int):
    if current_last_row < DATA_START_ROW:
        return

    set_row_background(ws, DATA_START_ROW, current_last_row, end_col, DEFAULT_BG_COLOR)

    new_start_row = max(previous_last_row + 1, DATA_START_ROW)
    if current_last_row >= new_start_row:
        set_row_background(ws, new_start_row, current_last_row, end_col, HIGHLIGHT_BG_COLOR)


def update_run_status(ws, now: str, status: str):
    ws.update(values=[["Last Run", now], ["Last Result", status]], range_name="A2:B3")


def main():
    sa_files = glob.glob(SERVICE_ACCOUNT_GLOB)
    if not sa_files:
        raise SystemExit("No Firebase service account JSON found in repo root")

    gc = gspread.service_account(filename=sa_files[0])
    sh = gc.open_by_key(SHEET_ID)

    results = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sheet_name, cfg in WORKSHEETS.items():
        ws = sh.worksheet(sheet_name)
        raw_value = ws.acell("B1").value
        count = parse_count(raw_value)
        previous_last_row = last_nonempty_row(ws)
        update_run_status(ws, now, "Running")

        if count == 0:
            update_run_status(ws, now, "Skipped (B1=0)")
            results.append(f"{sheet_name}: skipped (B1=0)")
            continue

        try:
            if cfg["mode"] == "batch":
                cmd = cfg["command"] + [str(count)]
                proc = run_command(cmd)
                if proc.returncode != 0:
                    tail = (proc.stderr or proc.stdout or "").strip()[-500:]
                    raise RuntimeError(f"failed running {' '.join(cmd)}: {tail}")
                current_last_row = last_nonempty_row(ws)
                refresh_new_row_highlight(ws, cfg["columns"], previous_last_row, current_last_row)
                ws.update_acell("B1", "0")
                highlight_start = max(previous_last_row + 1, DATA_START_ROW)
                update_run_status(ws, now, f"Success: generated {count}")
                results.append(f"{sheet_name}: generated {count}, highlighted rows {highlight_start}-{current_last_row}, reset B1 to 0")
                continue

            remaining = count
            for i in range(count):
                proc = run_command(cfg["command"])
                if proc.returncode != 0:
                    tail = (proc.stderr or proc.stdout or "").strip()[-500:]
                    raise RuntimeError(
                        f"failed on run {i+1}/{count}; remaining count left in B1={remaining}. Error tail: {tail}"
                    )
                remaining -= 1
                ws.update_acell("B1", str(remaining))
                current_last_row = last_nonempty_row(ws)
                refresh_new_row_highlight(ws, cfg["columns"], previous_last_row, current_last_row)

            current_last_row = last_nonempty_row(ws)
            highlight_start = max(previous_last_row + 1, DATA_START_ROW)
            update_run_status(ws, now, f"Success: generated {count}")
            results.append(f"{sheet_name}: generated {count}, highlighted rows {highlight_start}-{current_last_row}, reset B1 to 0")
        except Exception as exc:
            current_last_row = last_nonempty_row(ws)
            if current_last_row > previous_last_row:
                refresh_new_row_highlight(ws, cfg["columns"], previous_last_row, current_last_row)
            update_run_status(ws, now, f"Error: {str(exc)[:120]}")
            results.append(f"{sheet_name}: {exc}")

    print(f"aiVid sheet generator run at {now}")
    for line in results:
        print(f"- {line}")


if __name__ == "__main__":
    main()
