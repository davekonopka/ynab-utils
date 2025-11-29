"""Integration tests for ynab-utils CLI commands."""

import json
import subprocess
from pathlib import Path

import pytest


def run_detect_dupes(file_path: str, *args) -> dict:
    """Run detect-dupes command and return parsed JSON output.

    Args:
        file_path: Path to CSV file
        *args: Additional command-line arguments

    Returns:
        Parsed JSON output from command
    """
    cmd = [
        "uv",
        "run",
        "ynab-utils",
        "detect-dupes",
        "--file",
        file_path,
        "--output",
        "json",
        *args,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


class TestDetectDupesIntegration:
    """Integration tests for detect-dupes subcommand."""

    def test_exact_duplicate_same_date(self):
        """Test detecting exact duplicates on the same date."""
        test_file = Path(__file__).parent / "data" / "duplicates_exact_same_date.csv"
        result = run_detect_dupes(str(test_file))

        assert result["duplicates_found"] == 1
        assert len(result["pairs"]) == 1

        pair = result["pairs"][0]
        assert pair["confidence"] == 5
        assert pair["transaction1"]["payee"] == "Starbucks"
        assert pair["transaction2"]["payee"] == "Starbucks"
        assert pair["transaction1"]["amount"] == -5.50
        assert pair["transaction2"]["amount"] == -5.50
        assert pair["transaction1"]["date"] == "2025-11-20"
        assert pair["transaction2"]["date"] == "2025-11-20"

    def test_fuzzy_payee_match(self):
        """Test detecting duplicates with fuzzy payee matching."""
        test_file = Path(__file__).parent / "data" / "duplicates_fuzzy_payee.csv"
        result = run_detect_dupes(str(test_file), "--confidence", "1")

        assert result["duplicates_found"] == 1
        assert len(result["pairs"]) == 1

        pair = result["pairs"][0]
        assert pair["confidence"] == 4  # Same date, fuzzy payee
        assert pair["transaction1"]["payee"] == "Starbucks"
        assert pair["transaction2"]["payee"] == "Starbuck"

    def test_duplicates_within_days_window(self):
        """Test detecting duplicates within date proximity window."""
        test_file = Path(__file__).parent / "data" / "duplicates_within_days.csv"
        result = run_detect_dupes(str(test_file), "--days", "2", "--confidence", "1")

        assert result["duplicates_found"] == 1
        assert len(result["pairs"]) == 1

        pair = result["pairs"][0]
        assert pair["confidence"] == 3  # Within window, exact payee
        assert pair["transaction1"]["payee"] == "Amazon"
        assert pair["transaction2"]["payee"] == "Amazon"
        assert pair["transaction1"]["date"] == "2025-11-20"
        assert pair["transaction2"]["date"] == "2025-11-22"

    def test_no_duplicates(self):
        """Test file with no duplicate transactions."""
        test_file = Path(__file__).parent / "data" / "no_duplicates.csv"
        result = run_detect_dupes(str(test_file))

        assert result["duplicates_found"] == 0
        assert len(result["pairs"]) == 0

    def test_confidence_filter(self):
        """Test filtering results by confidence level."""
        test_file = Path(__file__).parent / "data" / "duplicates_fuzzy_payee.csv"

        # With confidence=5, should find nothing (fuzzy match is confidence 4)
        result = run_detect_dupes(str(test_file), "--confidence", "5")
        assert result["duplicates_found"] == 0

        # With confidence=4, should find the fuzzy match
        result = run_detect_dupes(str(test_file), "--confidence", "4")
        assert result["duplicates_found"] == 1

        # With confidence=1, should find the fuzzy match
        result = run_detect_dupes(str(test_file), "--confidence", "1")
        assert result["duplicates_found"] == 1

    def test_start_date_filter(self):
        """Test filtering transactions by start date."""
        test_file = Path(__file__).parent / "data" / "duplicates_with_date_filter.csv"

        # Without filter, should find 2 duplicate pairs
        result = run_detect_dupes(str(test_file))
        assert result["duplicates_found"] == 2

        # With start date, should only find recent duplicates
        result = run_detect_dupes(str(test_file), "--start-date", "2025-11-01")
        assert result["duplicates_found"] == 1

        pair = result["pairs"][0]
        assert pair["transaction1"]["date"] == "2025-11-20"
        assert pair["transaction1"]["payee"] == "Recent Purchase"

    def test_days_window_adjustment(self):
        """Test adjusting the date proximity window."""
        test_file = Path(__file__).parent / "data" / "duplicates_within_days.csv"

        # With 1-day window, should not find duplicates (transactions 2 days apart)
        result = run_detect_dupes(str(test_file), "--days", "1", "--confidence", "1")
        assert result["duplicates_found"] == 0

        # With 3-day window, should find duplicates
        result = run_detect_dupes(str(test_file), "--days", "3", "--confidence", "1")
        assert result["duplicates_found"] == 1

    def test_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        with pytest.raises(subprocess.CalledProcessError):
            run_detect_dupes("/nonexistent/file.csv")

    def test_invalid_date_format(self):
        """Test error handling for invalid date format."""
        test_file = Path(__file__).parent / "data" / "no_duplicates.csv"
        with pytest.raises(subprocess.CalledProcessError):
            run_detect_dupes(str(test_file), "--start-date", "invalid-date")
