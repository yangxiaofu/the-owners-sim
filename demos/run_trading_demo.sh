#!/bin/bash

# Helper script to run trading view demo with correct PYTHONPATH
# Usage: ./demos/run_trading_demo.sh [scenario]
# Scenarios: default, win_now, rebuild, edge_cases

SCENARIO=${1:-default}

export PYTHONPATH=src:.
python demos/trading_view_demo.py "$SCENARIO"
