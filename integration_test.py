#!/usr/bin/env python3

import sys
import urllib.request

def print_test(func):
    def to_ret(*args, **kwargs):
        print(f"TEST: {func.__name__} {args} {kwargs}")
        return func(*args, **kwargs)
    return to_ret

@print_test
def release(res, num, auth):
    req = urllib.request.Request(f"http://localhost/release/{res}/{num}/{auth}")
    req.method = "DELETE"
    try:
        opened = urllib.request.urlopen(req)
        opened.read(1024)
        opened.close()
    except Exception as err:
        if "503" in str(err):
            return 503
        elif "400" in str(err):
            return 400
        elif "401" in str(err):
            return 401
        raise RuntimeError(f"Unknown err: {err}")
    else:
        return 200

@print_test
def reserve(res, auth):
    req = urllib.request.Request(f"http://localhost/reserve/{res}/{auth}")
    req.method = "POST"
    req.data = None
    try:
        opened = urllib.request.urlopen(req)
        result = opened.read(1024)
        opened.close()
        return int(result)
    except Exception as err:
        if "503" in str(err):
            return 503
        elif "400" in str(err):
            return 400
        elif "401" in str(err):
            return 401
        raise RuntimeError(f"Unknown err: {err}")
    raise RuntimeError("Execution should not be here")

def assert_eq(val1, val2):
    if val1 != val2:
        raise RuntimeError(f"{val1} != {val2}")

def part0():
    assert_eq(503, release("singleton_1", 0, "supersecret1"))
    assert_eq(401, reserve("singleton_1", "wrong_pass"))
    assert_eq(0, reserve("singleton_1", "supersecret1"))
    assert_eq(200, release("singleton_1", 0, "supersecret1"))
    assert_eq(503, release("singleton_1", 0, "supersecret1"))
    assert_eq(503, release("singleton_1", 1, "supersecret1"))
    assert_eq(503, release("singleton_1", 1000, "supersecret1"))
    assert_eq(400, release("singleton_1", -20, "supersecret1"))

    assert_eq(503, reserve("zero", "supersecret4"))
    assert_eq(401, reserve("zero", "supersecret3"))

    assert_eq(0, reserve("got10", "supersecret0"))
    assert_eq(1, reserve("got10", "supersecret0"))
    assert_eq(2, reserve("got10", "supersecret0"))
    assert_eq(200, release("got10", 1, "supersecret0"))
    assert_eq(3, reserve("got10", "supersecret0"))
    assert_eq(4, reserve("got10", "supersecret0"))
    assert_eq(5, reserve("got10", "supersecret0"))
    assert_eq(6, reserve("got10", "supersecret0"))
    assert_eq(200, release("got10", 2, "supersecret0"))
    assert_eq(200, release("got10", 4, "supersecret0"))
    assert_eq(7, reserve("got10", "supersecret0"))
    assert_eq(8, reserve("got10", "supersecret0"))
    assert_eq(9, reserve("got10", "supersecret0"))
    assert_eq(1, reserve("got10", "supersecret0"))
    assert_eq(200, release("got10", 7, "supersecret0"))
    assert_eq(2, reserve("got10", "supersecret0"))
    assert_eq(4, reserve("got10", "supersecret0"))
    assert_eq(7, reserve("got10", "supersecret0"))
    assert_eq(503, reserve("got10", "supersecret0"))
    assert_eq(200, release("got10", 8, "supersecret0"))

def part1():
    assert_eq(8, reserve("got10", "supersecret0"))
    assert_eq(503, reserve("got10", "supersecret0"))

if __name__ == "__main__":
    if sys.argv[1] == "0":
        part0()
    elif sys.argv[1] == "1":
        part1()