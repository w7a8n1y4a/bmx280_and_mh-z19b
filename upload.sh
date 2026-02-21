#!/usr/bin/env bash

PORT="${1:-/dev/ttyUSB0}"

ampy -p "$PORT" -b 115200 mkdir ./lib
ampy -p "$PORT" -b 115200 put ./lib/bmx280.py ./lib/bmx280.py
ampy -p "$PORT" -b 115200 put ./lib/mhz19b.py ./lib/mhz19b.py
ampy -p "$PORT" -b 115200 put ./main.py ./main.py
ampy -p "$PORT" -b 115200 put ./boot.py ./boot.py
ampy -p "$PORT" -b 115200 put ./env.json ./env.json
ampy -p "$PORT" -b 115200 put ./schema.json ./schema.json
ampy -p "$PORT" -b 115200 ls
