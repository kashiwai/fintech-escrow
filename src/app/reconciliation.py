import argparse
import csv
import os
from datetime import datetime, date

from .audit import append as audit
from .config import REPORTS_DIR
from .db import db


def run_for_date(target: date) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    out = os.path.join(REPORTS_DIR, f"recon_{target.isoformat()}.csv")
    with db() as conn, open(out, "w", newline="") as f:
        c = conn.cursor()
        writer = csv.writer(f)
        writer.writerow(["currency", "internal_total", "rapyd_total", "delta"])
        # Internal balances by currency
        c.execute(
            "SELECT currency, SUM(available) as total FROM balances GROUP BY currency"
        )
        internal = {row["currency"]: int(row["total"]) for row in c.fetchall()}
        # Rapyd simulated balances
        c.execute("SELECT currency, available FROM rapyd_balances")
        rapyd = {row["currency"]: int(row["available"]) for row in c.fetchall()}
        keys = set(internal.keys()) | set(rapyd.keys())
        for cur in sorted(keys):
            it = internal.get(cur, 0)
            rp = rapyd.get(cur, 0)
            delta = it - rp
            writer.writerow([cur, it, rp, delta])
    audit("reconciliation", target.isoformat(), {"file": out})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", help="run reconciliation", nargs="?")
    parser.add_argument("--date", default="today", help="ISO date or 'today'")
    args = parser.parse_args()
    if args.run is None:
        parser.print_help()
        return
    tgt = date.today() if args.date == "today" else datetime.fromisoformat(args.date).date()
    out = run_for_date(tgt)
    print(out)


if __name__ == "__main__":
    main()

