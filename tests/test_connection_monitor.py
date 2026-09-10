"""Tests for connection monitor."""

import time
import unittest

from bridge.connection_monitor import ConnectionMonitor, CONN_STALE_SEC


class TestConnectionMonitor(unittest.TestCase):
    def test_ds100_connected_after_rx(self) -> None:
        m = ConnectionMonitor()
        self.assertFalse(m.ds100_connected())
        m.note_activity("ds100_rx")
        self.assertTrue(m.ds100_connected())

    def test_stale_connection(self) -> None:
        m = ConnectionMonitor()
        m._ds100_rx_at = time.time() - CONN_STALE_SEC - 1
        self.assertFalse(m.ds100_connected())


if __name__ == "__main__":
    unittest.main()
