"""Tests for cyberpower_exporter.exporter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from prometheus_client import REGISTRY
import pytest

from cyberpower_exporter import exporter


SAMPLE_PWRSTATD_RESPONSE = b"""state=0
model_name=PR750LCD
firmware_num=PQ6BN2001641
battery_volt=24000
input_rating_volt=120000
output_rating_watt=525000
avr_supported=yes
online_type=no
diagnostic_result=1
diagnostic_date=2020/03/19 15:05:30
power_event_result=0
battery_remainingtime=621
battery_charging=no
battery_discharging=no
ac_present=yes
boost=no
buck=no
utility_volt=122000
output_volt=122000
load=50000
battery_capacity=100
"""


EXPECTED_COLLECTOR_KEYS = {
    "info",
    "utility_volt",
    "output_volt",
    "diagnostic_result",
    "battery_remaining_time",
    "battery_charging",
    "battery_discharging",
    "ac_present",
    "load",
    "battery_capacity",
    "input_rating_volt",
    "output_rating_watt",
}


# --------------------------------------------------------------------------- #
# register_prometheus_collectors                                              #
# --------------------------------------------------------------------------- #


class TestRegisterPrometheusCollectors:
    def test_registers_all_expected_keys(self) -> None:
        collectors = exporter.register_prometheus_collectors()
        assert set(collectors.keys()) == EXPECTED_COLLECTOR_KEYS

    def test_registers_each_metric_under_its_ups_name(self) -> None:
        exporter.register_prometheus_collectors()
        registered = REGISTRY._names_to_collectors  # type: ignore[attr-defined]

        for name in (
            "ups_utility_volt",
            "ups_output_volt",
            "ups_diagnostic_result",
            "ups_battery_remaining_time",
            "ups_battery_charging",
            "ups_battery_discharging",
            "ups_ac_present",
            "ups_load",
            "ups_battery_capacity",
            "ups_input_rating_volt",
            "ups_output_rating_watt",
        ):
            assert name in registered, f"missing {name}"


# --------------------------------------------------------------------------- #
# set_prometheus_values                                                       #
# --------------------------------------------------------------------------- #


class TestSetPrometheusValues:
    @pytest.fixture
    def parsed_data(self) -> dict[str, str]:
        return {
            "model_name": "PR750LCD",
            "firmware_num": "PQ6BN2001641",
            "utility_volt": "122000",
            "output_volt": "122000",
            "diagnostic_result": "1",
            "battery_remainingtime": "621",
            "battery_charging": "no",
            "battery_discharging": "no",
            "ac_present": "yes",
            "load": "50000",
            "battery_capacity": "100",
            "input_rating_volt": "120000",
            "output_rating_watt": "525000",
        }

    def test_writes_expected_gauge_values(self, parsed_data: dict[str, str]) -> None:
        collectors = exporter.register_prometheus_collectors()

        with patch.object(exporter, "get_data", return_value=parsed_data):
            exporter.set_prometheus_values(collectors)

        # Gauges that scale by /1000
        assert REGISTRY.get_sample_value("ups_utility_volt") == 122.0
        assert REGISTRY.get_sample_value("ups_output_volt") == 122.0
        assert REGISTRY.get_sample_value("ups_input_rating_volt") == 120.0
        assert REGISTRY.get_sample_value("ups_output_rating_watt") == 525.0

        # Direct casts
        assert REGISTRY.get_sample_value("ups_diagnostic_result") == 1.0
        assert REGISTRY.get_sample_value("ups_battery_remaining_time") == 621.0
        assert REGISTRY.get_sample_value("ups_battery_capacity") == 100.0

        # /100 scaling
        assert REGISTRY.get_sample_value("ups_load") == 500.0  # 50000 / 100

        # yes/no → 1/0
        assert REGISTRY.get_sample_value("ups_battery_charging") == 0.0
        assert REGISTRY.get_sample_value("ups_battery_discharging") == 0.0
        assert REGISTRY.get_sample_value("ups_ac_present") == 1.0

    def test_info_metric_carries_model_and_firmware(self, parsed_data: dict[str, str]) -> None:
        collectors = exporter.register_prometheus_collectors()

        with patch.object(exporter, "get_data", return_value=parsed_data):
            exporter.set_prometheus_values(collectors)

        sample = REGISTRY.get_sample_value(
            "ups_cyberpower_info",
            {"model_name": "PR750LCD", "firmware_num": "PQ6BN2001641"},
        )
        assert sample == 1.0

    def test_battery_charging_yes_maps_to_one(self, parsed_data: dict[str, str]) -> None:
        parsed_data["battery_charging"] = "yes"
        parsed_data["battery_discharging"] = "yes"
        parsed_data["ac_present"] = "no"
        collectors = exporter.register_prometheus_collectors()

        with patch.object(exporter, "get_data", return_value=parsed_data):
            exporter.set_prometheus_values(collectors)

        assert REGISTRY.get_sample_value("ups_battery_charging") == 1.0
        assert REGISTRY.get_sample_value("ups_battery_discharging") == 1.0
        assert REGISTRY.get_sample_value("ups_ac_present") == 0.0


# --------------------------------------------------------------------------- #
# get_data                                                                    #
# --------------------------------------------------------------------------- #


class TestGetData:
    def _make_socket(self, payload: bytes, *, chunk_size: int = 4096) -> MagicMock:
        """Build a MagicMock that behaves like a context-managed socket.

        ``recv`` returns the payload one chunk at a time, then b"" to signal EOF.
        """
        sock = MagicMock()
        chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]
        chunks.append(b"")  # EOF
        sock.recv.side_effect = chunks
        sock.__enter__.return_value = sock
        sock.__exit__.return_value = False
        return sock

    def test_parses_pwrstatd_status_payload(self) -> None:
        sock = self._make_socket(SAMPLE_PWRSTATD_RESPONSE)

        with patch("cyberpower_exporter.exporter.socket.socket", return_value=sock):
            data = exporter.get_data()

        assert data["model_name"] == "PR750LCD"
        assert data["firmware_num"] == "PQ6BN2001641"
        assert data["utility_volt"] == "122000"
        assert data["output_volt"] == "122000"
        assert data["battery_capacity"] == "100"
        assert data["ac_present"] == "yes"
        assert data["battery_charging"] == "no"

    def test_sends_status_command_to_unix_socket(self) -> None:
        sock = self._make_socket(SAMPLE_PWRSTATD_RESPONSE)

        with patch("cyberpower_exporter.exporter.socket.socket", return_value=sock):
            exporter.get_data()

        sock.connect.assert_called_once_with(exporter.POWER_STAT_SOCKET)
        sock.sendall.assert_called_once_with(exporter.STATUS_COMMAND)

    def test_handles_response_split_across_multiple_recv_chunks(self) -> None:
        # Force the response to come in 16-byte chunks to exercise the recv loop.
        sock = self._make_socket(SAMPLE_PWRSTATD_RESPONSE, chunk_size=16)

        with patch("cyberpower_exporter.exporter.socket.socket", return_value=sock):
            data = exporter.get_data()

        assert data["model_name"] == "PR750LCD"
        # Our payload is well over 16 bytes, so recv must have been called many times.
        assert sock.recv.call_count > 4

    def test_skips_blank_and_malformed_lines(self) -> None:
        payload = b"key1=val1\n\nthis-line-has-no-equals\nkey2=val2\n"
        sock = self._make_socket(payload)

        with patch("cyberpower_exporter.exporter.socket.socket", return_value=sock):
            data = exporter.get_data()

        assert data == {"key1": "val1", "key2": "val2"}

    def test_strips_whitespace_around_keys_and_values(self) -> None:
        payload = b"  spaced_key  =  spaced value  \n"
        sock = self._make_socket(payload)

        with patch("cyberpower_exporter.exporter.socket.socket", return_value=sock):
            data = exporter.get_data()

        assert data == {"spaced_key": "spaced value"}

    def test_only_splits_on_first_equals(self) -> None:
        payload = b"key=value=with=equals\n"
        sock = self._make_socket(payload)

        with patch("cyberpower_exporter.exporter.socket.socket", return_value=sock):
            data = exporter.get_data()

        assert data == {"key": "value=with=equals"}

    def test_returns_empty_dict_when_socket_returns_nothing(self) -> None:
        sock = self._make_socket(b"")

        with patch("cyberpower_exporter.exporter.socket.socket", return_value=sock):
            data = exporter.get_data()

        assert data == {}
