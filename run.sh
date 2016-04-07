#!/bin/bash

echo "> Git pull:"
git pull || true
echo ""
echo "> Kill previous one:"
kill -9 `cat pid.log` || true
echo ""
echo "> Run server:"
nohup python3.5 uno_server.py > nohup.log &
echo $! > pid.log
echo ""
echo "> Track the output:"
tail -f nohup.log || true
echo ""
echo "> End <"