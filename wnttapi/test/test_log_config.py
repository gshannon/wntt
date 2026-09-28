# ruff: noqa: I001
import test._bootstrap as boot

import logging
from unittest import TestCase

import app.log_config as lc

target_logger_name = "app.surge_logger"


class TestLogConfig(TestCase):
    def setUp(self):
        lc._last_mtime = None
        logging.getLogger(target_logger_name).setLevel(logging.INFO)

    def test_missing_file_is_noop(self):
        lc.refresh_log_levels(filepath=f"{boot.test_data_dir}/no-such-file.json")
        self.assertEqual(logging.getLogger(target_logger_name).level, logging.INFO)

    def test_malformed_json_is_noop(self):
        lc.refresh_log_levels(filepath=f"{boot.test_data_dir}/log_levels-bad.json")
        self.assertEqual(logging.getLogger(target_logger_name).level, logging.INFO)

    def test_invalid_level_is_skipped(self):
        lc.refresh_log_levels(filepath=f"{boot.test_data_dir}/log_levels-invalid-level.json")
        self.assertEqual(logging.getLogger(target_logger_name).level, logging.INFO)

    def test_valid_file_applies_level(self):
        lc.refresh_log_levels(filepath=f"{boot.test_data_dir}/log_levels-good.json")
        self.assertEqual(logging.getLogger(target_logger_name).level, logging.DEBUG)

    def test_unchanged_mtime_is_skipped(self):
        path = f"{boot.test_data_dir}/log_levels-good.json"
        lc.refresh_log_levels(filepath=path)
        self.assertEqual(logging.getLogger(target_logger_name).level, logging.DEBUG)

        # Reset the level directly (bypassing refresh_log_levels) then call again with the
        # same unchanged file; since mtime hasn't changed, the level should NOT be reapplied.
        logging.getLogger(target_logger_name).setLevel(logging.INFO)
        lc.refresh_log_levels(filepath=path)
        self.assertEqual(logging.getLogger(target_logger_name).level, logging.INFO)
