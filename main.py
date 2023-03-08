#!/usr/bin/env python3

import argparse
import collections
import configparser
import http.server
import json
import logging
import os
import re
import signal

def save_resources(f):
    def ret(*args, **kwargs):
        result = f(*args, **kwargs)
        Resources.save_resources()
        return result
    return ret

class Resources:
    all_resources = None
    readwrite_file = None

    @classmethod
    def validate_setup(cls):
        if cls.all_resources is None:
            raise RuntimeError("Set all_resources first!")
        if cls.readwrite_file is None:
            raise RuntimeError("Set readwrite_file first!")

    @classmethod
    def save_resources(cls):
        cls.validate_setup()
        cls.readwrite_file.seek(0)
        cls.readwrite_file.truncate()
        serializable = {
            name: res.make_ser()
            for name, res in cls.all_resources.items()
        }
        cls.readwrite_file.write(json.dumps(serializable))
        cls.readwrite_file.truncate()
        cls.readwrite_file.flush()
        cls.readwrite_file.seek(0)

    @classmethod
    def read_save_file(cls):
        cls.validate_setup()
        cls.readwrite_file.seek(0)
        read_dat = cls.readwrite_file.read()
        if len(read_dat.strip()) == 0:
            return
        data = json.loads(read_dat)
        saved_resources = {
            name: Resource(indict=entry)
            for name, entry in data.items()
        }
        for name, entry in saved_resources.items():
            if name not in cls.all_resources:
                logging.warning(f"Save file contains resource not in config: {name}")
            if entry.name != name:
                logging.warning(f"Save file contains resource with name mismatch: {name} {entry['name']}")
            if entry.count != cls.all_resources[name].count:
                logging.warning(f"Save file contains resource with count mismatch: {name}")
            cls.all_resources[name].allocations = entry.allocations
        for name in cls.all_resources:
            if name not in saved_resources:
                logging.warning(f"Config contains resource not in save file: {name}")


class Resource(dict):
    def __init__(self, name=None, count=None, auth_token=None, indict=None):
        if indict is not None:
            self.name = indict["name"]
            self.count = indict["count"]
            self.auth_token = indict["auth_token"]
            self.allocations = collections.deque(indict["allocations"])
            return
        self.name = name
        self.count = int(count)
        self.auth_token = auth_token
        self.allocations = collections.deque(range(self.count))

    @save_resources
    def allocate(self):
        if len(self.allocations) == 0:
            return None
        alloc = self.allocations.popleft()
        return alloc

    @save_resources
    def release(self, index):
        if index in self.allocations:
            return False
        if index >= self.count or index < 0:
            return False
        self.allocations.append(index)
        return True

    def make_ser(self):
        return {"name": self.name, "count": self.count,
            "auth_token": self.auth_token,
            "allocations": list(self.allocations)}

    def validate_auth(self, token):
        return token == self.auth_token

class ReservationHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        pattern = r"^/reserve/(?P<resource>.+)/(?P<auth_token>.+)$"
        path_match = re.fullmatch(pattern, self.path)

        if path_match is not None:
            if len(path_match.groups()) != 2:
                self.log_error(f"Fewer than 2 groups matched: {self.path}")
                self.send_response(400, "Bad Request")
                self.end_headers()
                return
            
            if not self.check_auth(path_match.groupdict()["resource"],
                    path_match.groupdict()["auth_token"]):
                self.log_error(f"Invalid auth token: {self.path}")
                self.send_response(401, "Unauthorized")
                self.end_headers()
                return
            
            self.do_reserve(path_match.groupdict()["resource"])
            return

        if path_match is None:
            self.log_error(f"Path match failed: {self.path}")
            self.send_response(400, "Bad Request")
            self.end_headers()
            return

    def do_DELETE(self):
        pattern = "^/release/(?P<resource>.+)/(?P<allocation>[0-9]+)/(?P<auth_token>.+)$"
        path_match = re.fullmatch(pattern, self.path)

        if path_match is not None:
            if len(path_match.groups()) != 3:
                self.log_error(f"Fewer than 3 groups matched: {self.path}")
                self.send_response(400, "Bad Request")
                self.end_headers()
                return

            if not self.check_auth(path_match.groupdict()["resource"],
                    path_match.groupdict()["auth_token"]):
                self.log_error(f"Invalid auth token: {self.path}")
                self.send_response(401, "Unauthorized")
                self.end_headers()
                return

            self.do_release(path_match.groupdict()["resource"],
                int(path_match.groupdict()["allocation"]))
            return

        if path_match is None:
            self.log_error(f"Path match failed: {self.path}")
            self.send_response(400, "Bad Request")
            self.end_headers()
            return

    def check_auth(self, resource_name, auth_token):
        if resource_name not in Resources.all_resources:
            return False
        return Resources.all_resources[resource_name].validate_auth(auth_token)

    def do_reserve(self, resource_name):
        if resource_name in Resources.all_resources:
            allocation = Resources.all_resources[resource_name].allocate()
            if allocation is None:
                self.log_error(f"No allocation available: {resource_name}")
                self.send_response(503, "Resource unavailable")
                self.end_headers()
                return
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"{allocation}".encode("utf-8"))
            return
        else:
            self.log_error(f"Unknown resource requested: {resource_name}")
            self.send_response(503, "Resource unavailable")
            self.end_headers()
            return

    def do_release(self, resource_name, allocation):
        if resource_name in Resources.all_resources:
            success = Resources.all_resources[resource_name].release(allocation)
            if not success:
                self.log_error(f"Release failed: {resource_name}")
                self.send_response(503, "Resource unavailable")
                self.end_headers()
                return
            
            self.send_response(200)
            self.end_headers()
            return
        else:
            self.log_error(f"Unknown resource requested: {resource_name}")
            self.send_response(503, "Resource unavailable")
            self.end_headers()
            return

if __name__ == "__main__":
    """
    Needed inputs - list of: resource name, max count
    """
    port = int(os.environ.get("PORT","8080"))
    host = os.environ.get("HOST","")

    parser = argparse.ArgumentParser()
    parser.add_argument('configfile', type=argparse.FileType("r"))
    parser.add_argument('savefile', type=argparse.FileType("a+"))
    
    args = parser.parse_args()

    config = json.loads(args.configfile.read())
    config_resources = config["resources"]

    Resources.all_resources = {
        res["name"]: Resource(res["name"], res["count"], res["auth_token"])
        for res in config_resources
    }

    Resources.readwrite_file = args.savefile
    Resources.read_save_file()

    server = http.server.ThreadingHTTPServer((host, port), ReservationHandler)
    def server_term_func(signum, frame):
        thr = threading.Thread(target=lambda: server.shutdown())
        thr.run()
        thr.join()
    signal.signal(signal.SIGTERM, server_term_func)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        pass
    server.server_close()