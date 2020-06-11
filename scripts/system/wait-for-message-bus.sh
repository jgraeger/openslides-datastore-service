#!/bin/bash

export MESSAGE_BUS_PORT=${MESSAGE_BUS_PORT:-6379}
export MESSAGE_BUS_HOST=${MESSAGE_BUS_HOST:-redis}
wait-for-it --timeout=15 "$MESSAGE_BUS_HOST:$MESSAGE_BUS_PORT"
