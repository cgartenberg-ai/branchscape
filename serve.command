#!/bin/bash
# Double-click this file (macOS) to launch BRANCHSCAPE locally.
# It starts a small web server in this folder and opens your browser.
cd "$(dirname "$0")"
PORT=8000
echo "BRANCHSCAPE  ->  http://localhost:$PORT/"
echo "   (offline/bulletproof mode: http://localhost:$PORT/?offline )"
echo "Leave this window open during the demo. Close it to stop the server."
# open the browser shortly after the server starts
( sleep 1.2; open "http://localhost:$PORT/" ) &
python3 -m http.server $PORT
