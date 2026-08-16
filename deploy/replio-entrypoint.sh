#!/bin/sh
set -e

if [ -n "$REPLIO_PATH" ]; then
  exec replio serve --host "$REPLIO_HOST" --port "$REPLIO_PORT" --path "$REPLIO_PATH"
fi

exec replio serve --host "$REPLIO_HOST" --port "$REPLIO_PORT"
