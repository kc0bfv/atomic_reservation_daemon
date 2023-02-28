#!/usr/bin/env python3

import argparse
import configparser
import http.server
import os
import signal

class Resource:
    def __init__(self, name, count):
        self.name = name
        self.count = count

class ReservationHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        pattern = "^/reserve/(.*)$"
        path_match = re.fullmatch(pattern, self.path)

        if path_match is not None:
            if len(path_match.groups()) != 1:
                self.log_error(f"No groups matched: {self.path}")
                self.send_response(400, "Bad Request")
                self.end_headers()
                return
            
            do_reserve(path_match.groups()[0])
            return

        if path_match is None:
            self.log_error(f"Path match failed: {self.path}")
            self.send_response(400, "Bad Request")
            self.end_headers()
            return

    def do_DELETE(self):
        pattern = "^/release/(.*)/(.*)$"
        path_match = re.fullmatch(pattern, self.path)

        if path_match is not None:
            if len(path_match.groups()) != 2:
                self.log_error(f"Fewer than two groups matched: {self.path}")
                self.send_response(400, "Bad Request")
                self.end_headers()
                return
            
            do_release(path_match.groups()[0], path_match.groups()[1])
            return

        if path_match is None:
            self.log_error(f"Path match failed: {self.path}")
            self.send_response(400, "Bad Request")
            self.end_headers()
            return

    def do_reserve(self, resource_name):
        if resource_name in self.resources:
            allocation = self.resources[resource_name].allocate()
            if allocation is None:
                self.log_error(f"No allocation available: {resource_name}")
                self.send_response(503, "Resource unavailable")
                self.end_headers()
                return
            
            self.send_response(200)
            self.wfile.write(f"{allocation}".encode("utf-8"))
            return
        else:
            self.log_error(f"Unknown resource requested: {resource_name}")
            self.send_response(503, "Resource unavailable")
            self.end_headers()
            return

    def do_release(self, resource_name, allocation):
        if resource_name in self.resources:
            success = self.resources[resource_name].release(allocation)
            if not success:
                self.log_error(f"Release failed: {resource_name}")
                self.send_response(503, "Resource unavailable")
                self.end_headers()
                return
            
            self.send_response(200)
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
    port = int(os.environ.get("PORT","80"))
    host = os.environ.get("HOST","")

    parser = argparse.ArgumentParser()
    parser.add_argument('configfile', nargs="?", type=argparse.FileType("r"),
        default="-")
    
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read_string(args.configfile.read())

    config_resources = config.items("resources")

    resources = {name: Resource(name, count) for (name, count) in config_resources}

    ReservationHandler.resources = resources

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