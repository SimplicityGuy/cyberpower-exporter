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

from os import getenv
from socket import AF_UNIX, SOCK_STREAM, socket
from time import sleep

from prometheus_client import Gauge, Info, start_http_server

POWER_STAT_SOCKET = "/var/pwrstatd.ipc"
STATUS_COMMAND = b"STATUS\n\n"


def main():
    start_http_server(9200, addr="0.0.0.0")
    collectors = register_prometheus_collectors()
    while True:
        try:
            set_prometheus_values(collectors)
        except Exception as e:
            print(f"Error polling UPS: {e}")
        sleep(int(getenv("POLL_INTERVAL", 5)))


def register_prometheus_collectors():
    collectors = {}
    collectors["info"] = Info("ups_cyberpower", "Information about UPS")
    collectors["utility_volt"] = Gauge("ups_utility_volt", "Voltage from the utility")
    collectors["output_volt"] = Gauge("ups_output_volt", "Voltage output")
    collectors["diagnostic_result"] = Gauge(
        "ups_diagnostic_result", "Result of last diagnostic"
    )
    collectors["battery_remaining_time"] = Gauge(
        "ups_battery_remaining_time", "Seconds of battery time remaining"
    )
    collectors["battery_charging"] = Gauge(
        "ups_battery_charging", "Is battery charging"
    )
    collectors["battery_discharging"] = Gauge(
        "ups_battery_discharging", "Is battery discharging"
    )
    collectors["ac_present"] = Gauge("ups_ac_present", "Is AC power present")
    collectors["load"] = Gauge("ups_load", "Load percentage")
    collectors["battery_capacity"] = Gauge(
        "ups_battery_capacity", "Percentage of battery remaining"
    )
    collectors["input_rating_volt"] = Gauge(
        "ups_input_rating_volt", "Input voltage rating"
    )
    collectors["output_rating_watt"] = Gauge(
        "ups_output_rating_watt", "Output watts rating"
    )
    return collectors


def set_prometheus_values(collectors):
    data = get_data()
    collectors["info"].info(
        {
            "model_name": data["model_name"],
            "firmware_num": data["firmware_num"],
        }
    )
    collectors["utility_volt"].set(float(data["utility_volt"]) / 1000)
    collectors["output_volt"].set(float(data["output_volt"]) / 1000)
    collectors["diagnostic_result"].set(int(data["diagnostic_result"]))
    collectors["battery_remaining_time"].set(int(data["battery_remainingtime"]))
    collectors["battery_charging"].set(1 if data["battery_charging"] == "yes" else 0)
    collectors["battery_discharging"].set(
        1 if data["battery_discharging"] == "yes" else 0
    )
    collectors["ac_present"].set(1 if data["ac_present"] == "yes" else 0)
    collectors["load"].set(float(data["load"]) / 100)
    collectors["battery_capacity"].set(float(data["battery_capacity"]))
    collectors["output_rating_watt"].set(float(data["output_rating_watt"]) / 1000)
    collectors["input_rating_volt"].set(float(data["input_rating_volt"]) / 1000)


def get_data():
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

    chunks = []
    result = {}

    with socket(AF_UNIX, SOCK_STREAM) as s:
        s.connect(POWER_STAT_SOCKET)
        s.sendall(STATUS_COMMAND)
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)

    data = b"".join(chunks)
    for line in data.decode("ascii").splitlines():
        col = line.split("=", 1)
        if len(col) != 2:
            continue
        result[col[0].strip()] = col[1].strip()

    return result


if __name__ == "__main__":
    main()
