import glob
import subprocess
from datetime import datetime

import gspread

SHEET_ID = "1h1pPMEshYzfCyqA-xc4NHVcGotQk_-S_LzfFhPaPlhQ"
REPO_DIR = "/opt/data/aiVid-main"
SERVICE_ACCOUNT_GLOB = "/opt/data/aiVid-main/*-firebase-adminsdk-*.json"
MAX_GENERATE_COUNT = 10

WORKSHEETS = {
    "USA Male Ads": {"mode": "loop", "command": ["python3", "generate_v2.py"]},
    "Latam Female Ads": {"mode": "loop", "command": ["python3", "generate_v3.py"]},
    "V4 Ads": {"mode": "batch", "command": ["python3", "generate_v4.py"]},
    "V5 Ads": {"mode": "loop", "command": ["python3", "generate_v5.py"]},
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
        ws.update(values=[['Last Run', now]], range_name='A2:B2')

        if count == 0:
            results.append(f"{sheet_name}: skipped (B1=0)")
            continue

        if cfg["mode"] == "batch":
            cmd = cfg["command"] + [str(count)]
            proc = run_command(cmd)
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or "").strip()[-500:]
                raise RuntimeError(f"{sheet_name} failed running {' '.join(cmd)}: {tail}")
            ws.update_acell("B1", "0")
            results.append(f"{sheet_name}: generated {count}, reset B1 to 0")
            continue

        remaining = count
        for i in range(count):
            proc = run_command(cfg["command"])
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or "").strip()[-500:]
                raise RuntimeError(
                    f"{sheet_name} failed on run {i+1}/{count}; remaining count left in B1={remaining}. Error tail: {tail}"
                )
            remaining -= 1
            ws.update_acell("B1", str(remaining))

        results.append(f"{sheet_name}: generated {count}, reset B1 to 0")

    print(f"aiVid sheet generator run at {now}")
    for line in results:
        print(f"- {line}")


if __name__ == "__main__":
    main()
