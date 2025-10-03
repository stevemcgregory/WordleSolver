#!/bin/bash
set -e
docker compose build --pull streamlit
docker compose up -d streamlit