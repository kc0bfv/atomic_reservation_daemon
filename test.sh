#!/bin/bash

rm -f .testsavefile

python3 main.py config.json .testsavefile &
sleep .1
PYTHONPROC=$!
./integration_test.py 0
RES_0=$?
sleep .1
kill $PYTHONPROC

python3 main.py config.json .testsavefile &
sleep .1
PYTHONPROC=$!
./integration_test.py 1
RES_1=$?
sleep .1
kill $PYTHONPROC

if [ "$RES_0" -ne "0" ] || [ "$RES_1" -ne "0" ]; then
    echo "Test failure"
    exit 1
else
    echo "Test success"
fi