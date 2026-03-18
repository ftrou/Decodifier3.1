#!/usr/bin/env bash
set -euo pipefail

uvicorn engine.app.main:app --reload
