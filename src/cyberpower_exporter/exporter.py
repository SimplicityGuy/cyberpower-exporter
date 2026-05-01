# Copyright 2020 Mike Shoup
# Modifications by Robert Wlodarczyk
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import logging
import os
import socket
import time

from prometheus_client import Gauge, Info, start_http_server


POWER_STAT_SOCKET = "/var/pwrstatd.ipc"
STATUS_COMMAND = b"STATUS\n\n"
LISTEN_PORT = 9200
DEFAULT_POLL_INTERVAL = 5

logger = logging.getLogger(__name__)

Collectors = dict[str, Gauge | Info]


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Bind on all interfaces so the exporter is reachable from outside the container.
    start_http_server(LISTEN_PORT, addr="0.0.0.0")  # noqa: S104
    collectors = register_prometheus_collectors()
    interval = int(os.getenv("POLL_INTERVAL", str(DEFAULT_POLL_INTERVAL)))
    while True:
        try:
            set_prometheus_values(collectors)
        except Exception:
            logger.exception("Error polling UPS")
        time.sleep(interval)


def register_prometheus_collectors() -> Collectors:
    return {
        "info": Info("ups_cyberpower", "Information about UPS"),
        "utility_volt": Gauge("ups_utility_volt", "Voltage from the utility"),
        "output_volt": Gauge("ups_output_volt", "Voltage output"),
        "diagnostic_result": Gauge("ups_diagnostic_result", "Result of last diagnostic"),
        "battery_remaining_time": Gauge("ups_battery_remaining_time", "Seconds of battery time remaining"),
        "battery_charging": Gauge("ups_battery_charging", "Is battery charging"),
        "battery_discharging": Gauge("ups_battery_discharging", "Is battery discharging"),
        "ac_present": Gauge("ups_ac_present", "Is AC power present"),
        "load": Gauge("ups_load", "Load percentage"),
        "battery_capacity": Gauge("ups_battery_capacity", "Percentage of battery remaining"),
        "input_rating_volt": Gauge("ups_input_rating_volt", "Input voltage rating"),
        "output_rating_watt": Gauge("ups_output_rating_watt", "Output watts rating"),
    }


def set_prometheus_values(collectors: Collectors) -> None:
    data = get_data()
    collectors["info"].info(  # type: ignore[union-attr]
        {
            "model_name": data["model_name"],
            "firmware_num": data["firmware_num"],
        }
    )
    collectors["utility_volt"].set(float(data["utility_volt"]) / 1000)  # type: ignore[union-attr]
    collectors["output_volt"].set(float(data["output_volt"]) / 1000)  # type: ignore[union-attr]
    collectors["diagnostic_result"].set(int(data["diagnostic_result"]))  # type: ignore[union-attr]
    collectors["battery_remaining_time"].set(int(data["battery_remainingtime"]))  # type: ignore[union-attr]
    collectors["battery_charging"].set(1 if data["battery_charging"] == "yes" else 0)  # type: ignore[union-attr]
    collectors["battery_discharging"].set(1 if data["battery_discharging"] == "yes" else 0)  # type: ignore[union-attr]
    collectors["ac_present"].set(1 if data["ac_present"] == "yes" else 0)  # type: ignore[union-attr]
    collectors["load"].set(float(data["load"]) / 100)  # type: ignore[union-attr]
    collectors["battery_capacity"].set(float(data["battery_capacity"]))  # type: ignore[union-attr]
    collectors["output_rating_watt"].set(float(data["output_rating_watt"]) / 1000)  # type: ignore[union-attr]
    collectors["input_rating_volt"].set(float(data["input_rating_volt"]) / 1000)  # type: ignore[union-attr]


def get_data() -> dict[str, str]:
    # Sample output:
    #  state=0
    #  model_name=PR750LCD
    #  firmware_num=PQ6BN2001641
    #  battery_volt=24000
    #  input_rating_volt=120000
    #  output_rating_watt=525000
    #  avr_supported=yes
    #  online_type=no
    #  diagnostic_result=1
    #  diagnostic_date=2020/03/19 15:05:30
    #  power_event_result=0
    #  battery_remainingtime=621
    #  battery_charging=no
    #  battery_discharging=no
    #  ac_present=yes
    #  boost=no
    #  buck=no
    #  utility_volt=122000
    #  output_volt=122000
    #  load=50000
    #  battery_capacity=100

    chunks: list[bytes] = []
    result: dict[str, str] = {}

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        # Defensive timeout so any future protocol regression surfaces as a
        # logged exception instead of a silent hang.
        sock.settimeout(5)
        sock.connect(POWER_STAT_SOCKET)
        sock.sendall(STATUS_COMMAND)
        # pwrstatd does not half-close after replying; without this shutdown
        # the recv loop below would block forever waiting for an EOF that
        # never comes.
        sock.shutdown(socket.SHUT_WR)
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)

    payload = b"".join(chunks)
    for line in payload.decode("ascii").splitlines():
        col = line.split("=", 1)
        if len(col) != 2:
            continue
        result[col[0].strip()] = col[1].strip()

    return result


if __name__ == "__main__":
    main()
