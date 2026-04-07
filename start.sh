#!/bin/bash
export PYTHONPATH="/app/python:${PYTHONPATH}"
exec uvicorn dsra1d.web.app:app --host 0.0.0.0 --port ${PORT:-8011}
