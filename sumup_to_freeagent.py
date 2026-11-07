#!/usr/bin/env python3
"""Convert a SumUp "Transactions report" CSV into a FreeAgent bank statement CSV.

Usage:
    python3 sumup_to_freeagent.py REPORT.csv [REPORT2.csv ...] [-o OUTPUT.csv]

Treats SumUp as its own bank account in FreeAgent. For every successful sale:
    +  gross sale amount           (explain as sales income)
    -  SumUp card fee              (explain as bank/finance charges)
For every payout batch:
    -  amount paid to your bank    (explain as a transfer to your main bank account)
    -  amount SumUp withheld       ("Adjusted" rows, e.g. cash advance repayments)

Failed / cancelled sales are skipped. Output format matches FreeAgent's
template: no header, columns Date (dd/mm/yyyy), Amount, Description.
"""

import argparse
import csv
import sys
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {"Date", "Transaction ID", "Transaction type", "Status",
            "Description", "Total", "Fee", "Payout", "Payout date", "Payout ID"}
SKIP_STATUSES = {"failed", "cancelled", "canceled", "declined"}


def money(value):
    value = (value or "").strip()
    if not value:
        return Decimal("0")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError(f"not a number: {value!r}")


def uk_date(value):
    """'2026-11-06 17:59:15' or '2026-11-06' -> '06/11/2026'."""
    return datetime.strptime(value.strip()[:10], "%Y-%m-%d").strftime("%d/%m/%Y")


def clean(text):
    # FreeAgent's importer is happiest without commas/quotes in the description.
    return " ".join((text or "").replace(",", " ").replace('"', "").split())


def fmt(amount):
    return f"{amount.quantize(Decimal('0.01')):f}"


def convert(paths):
    """Return (rows, warnings). rows are (sort_key, date, amount, description)."""
    rows, warnings = [], []
    payouts = OrderedDict()   # (timestamp, payout id) -> [date, total]
    withheld = OrderedDict()  # (timestamp, date) -> total
    seen = set()

    for path in paths:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            missing = REQUIRED - set(reader.fieldnames or [])
            if missing:
                sys.exit(f"{path}: this doesn't look like the full SumUp "
                         f"'Transactions report' (missing columns: "
                         f"{', '.join(sorted(missing))}).\nUse the detailed SumUp "
                         f"transactions export that includes Fee and Payout ID columns.")

            for n, r in enumerate(reader, start=2):
                key = tuple(r.get(k, "") for k in ("Date", "Transaction ID",
                                                   "Transaction type", "Status", "Total"))
                if key in seen:          # same row in two overlapping exports
                    continue
                seen.add(key)

                kind = r["Transaction type"].strip().lower()
                status = r["Status"].strip().lower()
                txn = r["Transaction ID"].strip()
                stamp = r["Date"].strip()
                where = f"{Path(path).name} line {n}"

                if kind == "sale":
                    if status in SKIP_STATUSES:
                        continue
                    if status != "successful":
                        warnings.append(f"{where}: sale {txn} has status "
                                        f"'{r['Status']}', included anyway")
                    total, fee = money(r["Total"]), money(r["Fee"])
                    desc = clean(r["Description"]) or "Card sale"
                    date = uk_date(stamp)
                    rows.append((stamp, date, total, f"SumUp sale {txn} {desc}"))
                    if fee:
                        rows.append((stamp, date, -fee, f"SumUp fee {txn}"))

                elif kind == "payout":
                    amount = money(r["Payout"])
                    date = uk_date(r["Payout date"] or stamp)
                    if status == "paid":
                        k = (stamp, r["Payout ID"].strip() or "SUMUP PAYOUT")
                        payouts.setdefault(k, [date, Decimal("0")])[1] += amount
                    elif status == "adjusted":
                        k = (stamp, date)
                        withheld[k] = withheld.get(k, Decimal("0")) + amount
                    else:
                        warnings.append(f"{where}: payout with status "
                                        f"'{r['Status']}' skipped - check it manually")

                elif kind in ("refund", "chargeback"):
                    if status in SKIP_STATUSES:
                        continue
                    amount = -abs(money(r["Total"]))
                    rows.append((stamp, uk_date(stamp), amount,
                                 f"SumUp {kind} {txn} {clean(r['Description'])}".strip()))
                    fee = money(r["Fee"])
                    if fee:
                        rows.append((stamp, uk_date(stamp), -abs(fee), f"SumUp fee {txn}"))

                else:
                    warnings.append(f"{where}: unknown transaction type "
                                    f"'{r['Transaction type']}' ({txn}) skipped")

    for (stamp, pid), (date, total) in payouts.items():
        rows.append((stamp, date, -total, f"Transfer to bank {pid}"))
    for (stamp, date), total in withheld.items():
        rows.append((stamp, date, -total, "SumUp held back from payout"))

    rows.sort(key=lambda r: (datetime.strptime(r[1], "%d/%m/%Y"), r[0]))
    return rows, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reports", nargs="+", help="SumUp transactions report CSV file(s)")
    ap.add_argument("-o", "--output", help="output file (default: <first report>-freeagent.csv)")
    args = ap.parse_args()

    rows, warnings = convert(args.reports)
    if not rows:
        sys.exit("No transactions found to convert.")

    out = Path(args.output) if args.output else \
        Path(args.reports[0]).with_name(Path(args.reports[0]).stem + "-freeagent.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        for _, date, amount, desc in rows:
            w.writerow([date, fmt(amount), desc])

    money_in = sum(r[2] for r in rows if r[2] > 0)
    money_out = sum(r[2] for r in rows if r[2] < 0)
    print(f"Wrote {len(rows)} lines to {out}")
    print(f"  Money in : {fmt(money_in)}")
    print(f"  Money out: {fmt(money_out)}")
    print(f"  Net change to SumUp balance: {fmt(money_in + money_out)}")
    for w_ in warnings:
        print("WARNING:", w_)


if __name__ == "__main__":
    main()
