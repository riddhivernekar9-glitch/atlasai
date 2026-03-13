#!/bin/bash

cd /Users/riddhi/Documents/AtlasAI_v1 || exit 1

source venv/bin/activate

PYTHONPATH=$(pwd) nohup uvicorn server.app:app --port 8000 > atlasai_run.log 2>&1 &

sleep 3

open "/Users/riddhi/Documents/AtlasAI_v1/client/atlasai-client/src-tauri/target/release/bundle/macos/atlasai-client.app"
