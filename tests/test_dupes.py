"""Unit tests for duplicate detection functionality."""

from datetime import datetime
from pathlib import Path

import pytest

from ynab_utils.dupes import (
    Transaction,
    calculate_confidence,
    find_duplicates,
    fuzzy_match_payee,
    parse_amount,
    read_transactions,
)


class TestParseAmount:
    """Tests for parse_amount function."""

    def test_parse_outflow_only(self):
        """Test parsing when only outflow has a value."""
        assert parse_amount("$25.50", "$0.00") == -25.50
        assert parse_amount("25.50", "0.00") == -25.50

    def test_parse_inflow_only(self):
        """Test parsing when only inflow has a value."""
        assert parse_amount("$0.00", "$100.00") == 100.00
        assert parse_amount("0.00", "100.00") == 100.00

    def test_parse_with_commas(self):
        """Test parsing amounts with comma separators."""
        assert parse_amount("$1,234.56", "$0.00") == -1234.56
        assert parse_amount("$0.00", "$2,500.00") == 2500.00

    def test_parse_empty_strings(self):
        """Test parsing empty or whitespace strings."""
        assert parse_amount("", "") == 0.0
        assert parse_amount("  ", "  ") == 0.0

    def test_parse_invalid_values(self):
        """Test parsing invalid numeric values."""
        assert parse_amount("invalid", "$0.00") == 0.0
        assert parse_amount("$0.00", "invalid") == 0.0

    def test_parse_both_zero(self):
        """Test parsing when both values are zero."""
        assert parse_amount("$0.00", "$0.00") == 0.0


class TestFuzzyMatchPayee:
    """Tests for fuzzy_match_payee function."""

    def test_exact_match(self):
        """Test exact payee name matches."""
        assert fuzzy_match_payee("Starbucks", "Starbucks") is True
        assert fuzzy_match_payee("Amazon", "Amazon") is True

    def test_case_insensitive_match(self):
        """Test case insensitive matching."""
        assert fuzzy_match_payee("Starbucks", "STARBUCKS") is True
        assert fuzzy_match_payee("Target", "target") is True

    def test_fuzzy_match_success(self):
        """Test fuzzy matching with similar names."""
        # These should pass with 0.8 threshold (very similar strings)
        assert fuzzy_match_payee("Starbucks", "Starbuck") is True  # 0.94 similarity
        assert fuzzy_match_payee("Walmart Store", "Walmart") is False  # Too different
        assert fuzzy_match_payee("Target #1234", "Target") is False  # Too different

    def test_fuzzy_match_failure(self):
        """Test fuzzy matching with dissimilar names."""
        assert fuzzy_match_payee("Starbucks", "Walmart") is False
        assert fuzzy_match_payee("Target", "CVS") is False

    def test_empty_payees(self):
        """Test with empty payee names."""
        assert fuzzy_match_payee("", "Starbucks") is False
        assert fuzzy_match_payee("Starbucks", "") is False
        assert fuzzy_match_payee("", "") is False

    def test_threshold_customization(self):
        """Test custom threshold values."""
        # Low threshold should match more loosely
        assert fuzzy_match_payee("ABC", "XYZ", threshold=0.1) is False
        # Lower threshold allows looser matching
        assert fuzzy_match_payee("Starbucks Coffee", "Starbucks", threshold=0.6) is True
        # High threshold requires closer match
        assert fuzzy_match_payee("Starbucks Coffee", "Starbucks", threshold=0.9) is False


class TestCalculateConfidence:
    """Tests for calculate_confidence function."""

    def test_confidence_5_same_date_exact_payee(self):
        """Test confidence 5: same date, amount, exact payee."""
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 5
        assert "exact payee" in reason.lower()

    def test_confidence_4_same_date_fuzzy_payee(self):
        """Test confidence 4: same date, amount, fuzzy payee."""
        # Use payees that are similar enough to trigger fuzzy match (>0.8 similarity)
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 20), "Starbuck", -5.50, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 4
        assert "fuzzy payee" in reason.lower()

    def test_confidence_3_same_date_no_payee(self):
        """Test confidence 3: same date, amount, no payee match."""
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 20), "Walmart", -5.50, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 3
        assert "same date and amount" in reason.lower()

    def test_confidence_3_within_window_exact_payee(self):
        """Test confidence 3: within days window, amount, exact payee."""
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 22), "Starbucks", -5.50, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 3
        assert "exact payee" in reason.lower()

    def test_confidence_2_within_window_fuzzy_payee(self):
        """Test confidence 2: within days window, amount, fuzzy payee."""
        # Use payees that are similar enough to trigger fuzzy match (>0.8 similarity)
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 21), "Starbuck", -5.50, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 2
        assert "fuzzy payee" in reason.lower()

    def test_confidence_1_within_window_no_payee(self):
        """Test confidence 1: within days window, amount, no payee."""
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 21), "Walmart", -5.50, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 1
        assert "no payee match" in reason.lower()

    def test_confidence_0_different_amounts(self):
        """Test confidence 0: different amounts."""
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -10.00, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 0

    def test_confidence_0_outside_window(self):
        """Test confidence 0: dates outside window."""
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Starbucks", -5.50, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 25), "Starbucks", -5.50, "", 2)
        confidence, reason = calculate_confidence(t1, t2, 2)
        assert confidence == 0

    def test_different_days_windows(self):
        """Test with different days window values."""
        t1 = Transaction("Account1", datetime(2025, 11, 20), "Store", -10.00, "", 1)
        t2 = Transaction("Account1", datetime(2025, 11, 24), "Store", -10.00, "", 2)

        # Should not match with 2-day window
        confidence, _ = calculate_confidence(t1, t2, 2)
        assert confidence == 0

        # Should match with 5-day window
        confidence, _ = calculate_confidence(t1, t2, 5)
        assert confidence == 3


class TestFindDuplicates:
    """Tests for find_duplicates function."""

    def test_no_duplicates(self):
        """Test with transactions that are not duplicates."""
        transactions = [
            Transaction("Account", datetime(2025, 11, 20), "Store1", -10.00, "", 1),
            Transaction("Account", datetime(2025, 11, 21), "Store2", -20.00, "", 2),
            Transaction("Account", datetime(2025, 11, 22), "Store3", -30.00, "", 3),
        ]
        duplicates = find_duplicates(transactions, 2)
        assert len(duplicates) == 0

    def test_single_duplicate_pair(self):
        """Test with one duplicate pair."""
        transactions = [
            Transaction("Account", datetime(2025, 11, 20), "Store", -10.00, "", 1),
            Transaction("Account", datetime(2025, 11, 20), "Store", -10.00, "", 2),
            Transaction("Account", datetime(2025, 11, 22), "Other", -20.00, "", 3),
        ]
        duplicates = find_duplicates(transactions, 2)
        assert len(duplicates) == 1
        assert duplicates[0].confidence == 5

    def test_multiple_duplicate_pairs(self):
        """Test with multiple duplicate pairs."""
        transactions = [
            Transaction("Account", datetime(2025, 11, 20), "Store", -10.00, "", 1),
            Transaction("Account", datetime(2025, 11, 20), "Store", -10.00, "", 2),
            Transaction("Account", datetime(2025, 11, 21), "Cafe", -5.00, "", 3),
            Transaction("Account", datetime(2025, 11, 21), "Cafe Coffee", -5.00, "", 4),
        ]
        duplicates = find_duplicates(transactions, 2)
        assert len(duplicates) == 2
        # Should be sorted by confidence (highest first)
        assert duplicates[0].confidence >= duplicates[1].confidence

    def test_sorting_by_confidence(self):
        """Test that duplicates are sorted by confidence."""
        transactions = [
            Transaction("Account", datetime(2025, 11, 20), "Store", -10.00, "", 1),
            Transaction("Account", datetime(2025, 11, 21), "Different", -10.00, "", 2),
            Transaction("Account", datetime(2025, 11, 22), "Exact", -20.00, "", 3),
            Transaction("Account", datetime(2025, 11, 22), "Exact", -20.00, "", 4),
        ]
        duplicates = find_duplicates(transactions, 2)
        assert len(duplicates) == 2
        # Exact match should be first (higher confidence)
        assert duplicates[0].confidence == 5
        assert duplicates[1].confidence == 1

    def test_empty_transaction_list(self):
        """Test with empty transaction list."""
        duplicates = find_duplicates([], 2)
        assert len(duplicates) == 0


class TestReadTransactions:
    """Tests for read_transactions function."""

    def test_read_valid_csv(self):
        """Test reading a valid CSV file."""
        test_file = Path(__file__).parent / "data" / "valid_transactions.csv"
        transactions = read_transactions(str(test_file))
        assert len(transactions) == 2
        assert transactions[0].payee == "Store"
        assert transactions[0].amount == -25.00
        assert transactions[1].payee == "Cafe"
        assert transactions[1].amount == 50.00

    def test_read_csv_with_empty_rows(self):
        """Test reading CSV with empty date rows (should be skipped)."""
        test_file = Path(__file__).parent / "data" / "transactions_with_empty_rows.csv"
        transactions = read_transactions(str(test_file))
        assert len(transactions) == 2

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        with pytest.raises(SystemExit):
            read_transactions("/nonexistent/path/file.csv")

    def test_row_numbers(self):
        """Test that row numbers are correctly assigned."""
        test_file = Path(__file__).parent / "data" / "transactions_for_row_numbers.csv"
        transactions = read_transactions(str(test_file))
        # Row numbers start at 2 (header is row 1)
        assert transactions[0].row_number == 2
        assert transactions[1].row_number == 3
