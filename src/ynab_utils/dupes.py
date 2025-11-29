"""Duplicate transaction detection for YNAB exports."""

import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


@dataclass
class Transaction:
    """Represents a YNAB transaction."""

    account: str
    date: datetime
    payee: str
    amount: float
    memo: str
    row_number: int

    def __str__(self) -> str:
        """Format transaction for display."""
        sign = "-" if self.amount < 0 else "+"
        return f"Row {self.row_number}: {self.date.strftime('%Y-%m-%d')} | " f"{self.payee:30s} | {sign}${abs(self.amount):.2f}"


@dataclass
class DuplicateMatch:
    """Represents a potential duplicate transaction pair."""

    transaction1: Transaction
    transaction2: Transaction
    confidence: int
    reason: str


def parse_amount(outflow: str, inflow: str) -> float:
    """Parse amount from outflow/inflow columns.

    Outflows are negative, inflows are positive.
    """
    outflow_val = 0.0
    inflow_val = 0.0

    if outflow and outflow.strip():
        # Remove currency symbols and commas
        cleaned = outflow.strip().replace("$", "").replace(",", "")
        try:
            outflow_val = float(cleaned)
        except ValueError:
            pass

    if inflow and inflow.strip():
        cleaned = inflow.strip().replace("$", "").replace(",", "")
        try:
            inflow_val = float(cleaned)
        except ValueError:
            pass

    # Outflows are negative, inflows are positive
    return inflow_val - outflow_val


def read_transactions(file_path: str) -> list[Transaction]:
    """Read transactions from YNAB CSV export."""
    transactions = []
    path = Path(file_path)

    if not path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                date_str = row.get("Date", "").strip()
                if not date_str:
                    continue

                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    print(
                        f"Warning: Invalid date format at row {idx}: {date_str}",
                        file=sys.stderr,
                    )
                    continue

                amount = parse_amount(row.get("Outflow", ""), row.get("Inflow", ""))

                transaction = Transaction(
                    account=row.get("Account", "").strip(),
                    date=date,
                    payee=row.get("Payee", "").strip(),
                    amount=amount,
                    memo=row.get("Memo", "").strip(),
                    row_number=idx,
                )
                transactions.append(transaction)

    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    return transactions


def fuzzy_match_payee(payee1: str, payee2: str, threshold: float = 0.8) -> bool:
    """Check if two payee names are a fuzzy match."""
    if not payee1 or not payee2:
        return False

    # Normalize for comparison
    p1 = payee1.lower().strip()
    p2 = payee2.lower().strip()

    # Exact match
    if p1 == p2:
        return True

    # Fuzzy match using SequenceMatcher
    ratio = SequenceMatcher(None, p1, p2).ratio()
    return ratio >= threshold


def calculate_confidence(t1: Transaction, t2: Transaction, days_window: int) -> tuple[int, str]:
    """Calculate confidence score (1-5) for duplicate match.

    Scoring:
    - 5: Same date, same amount, exact payee
    - 4: Same date, same amount, fuzzy payee
    - 3: Within days window, same amount, exact payee
    - 2: Within days window, same amount, fuzzy payee
    - 1: Within days window, same amount, no payee match
    """
    # Check amount match (must be exact for any duplicate)
    if t1.amount != t2.amount:
        return 0, ""

    # Check date proximity
    date_diff = abs((t1.date - t2.date).days)
    same_date = date_diff == 0
    within_window = date_diff <= days_window

    if not within_window:
        return 0, ""

    # Check payee match
    exact_payee = t1.payee.lower() == t2.payee.lower() if t1.payee and t2.payee else False
    fuzzy_payee = fuzzy_match_payee(t1.payee, t2.payee) if not exact_payee else False

    # Calculate confidence and reason
    if same_date and exact_payee:
        return 5, "Same date, amount, and exact payee match"
    elif same_date and fuzzy_payee:
        return 4, "Same date, amount, and fuzzy payee match"
    elif same_date:
        return 3, "Same date and amount (no payee match)"
    elif within_window and exact_payee:
        return 3, f"Within {days_window} days, amount, and exact payee match"
    elif within_window and fuzzy_payee:
        return 2, f"Within {days_window} days, amount, and fuzzy payee match"
    elif within_window:
        return 1, f"Within {days_window} days, same amount (no payee match)"

    return 0, ""


def find_duplicates(transactions: list[Transaction], days_window: int) -> list[DuplicateMatch]:
    """Find potential duplicate transactions."""
    duplicates = []

    # Compare each transaction with all subsequent transactions
    for i, t1 in enumerate(transactions):
        for t2 in transactions[i + 1 :]:
            confidence, reason = calculate_confidence(t1, t2, days_window)
            if confidence > 0:
                duplicates.append(
                    DuplicateMatch(
                        transaction1=t1,
                        transaction2=t2,
                        confidence=confidence,
                        reason=reason,
                    )
                )

    # Sort by confidence (highest first), then by date (newest first)
    duplicates.sort(key=lambda d: (-d.confidence, -d.transaction1.date.timestamp()))

    return duplicates


def detect_duplicates(
    file_path: str,
    days_window: int,
    min_confidence: int = 5,
    start_date: str | None = None,
    output_format: str = "text",
) -> int:
    """Main function to detect and display duplicate transactions."""
    # Only print progress messages in text mode
    if output_format == "text":
        print(f"Reading transactions from: {file_path}")
        print(f"Date proximity window: {days_window} days")
        print(f"Minimum confidence level: {min_confidence}/5")

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            if output_format == "text":
                print(f"Filtering transactions from: {start_date}")
        except ValueError:
            if output_format == "text":
                print(
                    f"Error: Invalid date format '{start_date}'. Use YYYY-MM-DD",
                    file=sys.stderr,
                )
            else:
                print(
                    json.dumps({"error": f"Invalid date format '{start_date}'. Use YYYY-MM-DD"}),
                    file=sys.stderr,
                )
            return 1
    else:
        start_dt = None

    if output_format == "text":
        print()

    transactions = read_transactions(file_path)

    # Filter by start date if provided
    if start_dt:
        original_count = len(transactions)
        transactions = [t for t in transactions if t.date >= start_dt]
        if output_format == "text":
            print(f"Loaded {len(transactions)} transactions " f"(filtered from {original_count} by start date)\n")
    else:
        if output_format == "text":
            print(f"Loaded {len(transactions)} transactions\n")

    duplicates = find_duplicates(transactions, days_window)

    # Filter by minimum confidence
    duplicates = [d for d in duplicates if d.confidence >= min_confidence]

    if output_format == "json":
        # JSON output
        output = {
            "duplicates_found": len(duplicates),
            "pairs": [
                {
                    "confidence": dup.confidence,
                    "reason": dup.reason,
                    "transaction1": {
                        "row": dup.transaction1.row_number,
                        "date": dup.transaction1.date.strftime("%Y-%m-%d"),
                        "payee": dup.transaction1.payee,
                        "amount": dup.transaction1.amount,
                        "account": dup.transaction1.account,
                        "memo": dup.transaction1.memo,
                    },
                    "transaction2": {
                        "row": dup.transaction2.row_number,
                        "date": dup.transaction2.date.strftime("%Y-%m-%d"),
                        "payee": dup.transaction2.payee,
                        "amount": dup.transaction2.amount,
                        "account": dup.transaction2.account,
                        "memo": dup.transaction2.memo,
                    },
                }
                for dup in duplicates
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Text output
        if not duplicates:
            print("No potential duplicates found.")
            return 0

        print(f"Found {len(duplicates)} potential duplicate pair(s):\n")
        print("=" * 80)

        for idx, dup in enumerate(duplicates, start=1):
            print(f"\nDuplicate #{idx} (Confidence: {dup.confidence}/5)")
            print(f"Reason: {dup.reason}")
            print(f"  {dup.transaction1}")
            print(f"  {dup.transaction2}")
            print("-" * 80)

    return 0
