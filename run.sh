#!/bin/bash

echo "> Kill previous one:"
kill -9 `cat pid.log` || true
echo ""
echo "> Run server:"
nohup python3.5 uno_server.py > nohup.log &
echo $! > pid.log
echo ""
echo "> Track the output:"
tail nohup.log || true
echo ""
echo "> End <"