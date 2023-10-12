import time

from timestamps_tip_scanner.utils import one_time_tips

tips_lis = [(1000000000000000000, 1683037267, 1000000000000000000), (2000000000000000000, 1683037268, 3000000000000000000), (3000000000000000000, 1683037269, 6000000000000000000)]


def test_empty_list():
    """Test no tips in list"""
    timestamp = time.time()
    timestamp_before = time.time() - 100
    # should return false
    assert not one_time_tips([], timestamp, timestamp_before)


def test_valid_one_time_tip():
    """Test valid one-time tip"""
    timestamp = 1683037271  # timestamp is after tips were added
    timestamp_before = 1683037266  # timestamp is before tips were added
    # should return true
    assert one_time_tips(tips_lis, timestamp, timestamp_before)


def test_invalid_timestamp():
    # Test when both timestamps chasing the same tip
    timestamp = 1683037269  # report timestamp same as tip timestamp
    timestamp_before = 1683037268
    # should return false
    assert not one_time_tips(tips_lis, timestamp, timestamp_before)


def test_valid_timestamps():
    # Test when both timestamps are valid for a tip
    timestamp = 1683037270  # report timestamp same as tip timestamp
    timestamp_before = 1683037268
    # should return true
    assert one_time_tips(tips_lis, timestamp, timestamp_before)


def test_zero_tip_amount():
    """Test when tip amount is zero but timestamp is valid"""
    tips_lis = [(0, 1683037271, 0)]
    timestamp = 1683037272
    timestamp_before = 1683037270
    # should return false
    assert not one_time_tips(tips_lis, timestamp, timestamp_before)


def test_no_timestamp_before():
    """Test when timestamp_before is None"""
    timestamp = 1683037271
    timestamp_before = None
    assert one_time_tips(tips_lis, timestamp, timestamp_before)
