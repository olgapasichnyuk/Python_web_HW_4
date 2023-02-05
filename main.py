import json
import logging
import mimetypes
import pathlib
import socket
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

BASE_DIR = pathlib.Path()
SOCKET_SERVER_IP = '127.0.0.1'
SOCKET_SERVER_PORT = 5000
SOCKET_SERVER_ADDRESS = SOCKET_SERVER_IP, SOCKET_SERVER_PORT
JSON_STORAGE_FILE = pathlib.Path("./storage/data.json")


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self) -> None:

        route = urllib.parse.urlparse(self.path)
        client_request = route.path
        match client_request:
            case "/":
                self.send_html_file('./index.html')
            case '/message.html':
                self.send_html_file('./message.html')
            case _:
                file = pathlib.Path().joinpath(client_request[1:])
                if file.exists():

                    self.send_static(file)
                else:
                    self.send_html_file('./error.html', 404)

    def send_html_file(self, filename, status=200) -> None:

        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def do_POST(self):

        data = self.rfile.read(int(self.headers['Content-Length']))
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_client.sendto(data, SOCKET_SERVER_ADDRESS)
        socket_client.close()

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_static(self, file):

        self.send_response(200)
        guessed_mimotype, _ = mimetypes.guess_type(file)

        if guessed_mimotype:
            self.send_header("Content-type", guessed_mimotype)

        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()

        with open(f'{file}', 'rb') as file:
            self.wfile.write(file.read())


def run_http_server(server=HTTPServer, handler=HTTPRequestHandler):

    address = ('0.0.0.0', 3000)
    http_server = server(address, handler)

    try:
        http_server.serve_forever()

    except KeyboardInterrupt:
        http_server.server_close()


def run_socket_server():

    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_server.bind((SOCKET_SERVER_IP, SOCKET_SERVER_PORT))
    try:
        while True:
            data, address = socket_server.recvfrom(1024)
            storage_update_json(data)
    except KeyboardInterrupt:
        socket_server.close()
    finally:
        socket_server.close()


def storage_update_json(data):

    data_parse = urllib.parse.unquote_plus(data.decode())

    try:
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        dict_for_json = {str(datetime.now()): data_dict}
        
        try:
            with open(JSON_STORAGE_FILE, 'r', encoding='utf-8') as fd:
                loaded_dict = dict(json.loads(fd.read()))
                loaded_dict.update(dict_for_json)

        except json.decoder.JSONDecodeError:
            loaded_dict = dict_for_json

        with open(JSON_STORAGE_FILE, 'w', encoding='utf-8') as data_file_json:
            json.dump(loaded_dict, data_file_json, ensure_ascii=False)

    except ValueError as error:
        logging.error(f'Failed to load data:{error}')

    except OSError as error:
        logging.error(f'Failed to load data:{error}')


if __name__ == '__main__':
    
    logging.basicConfig(level=logging.DEBUG)
    
    server_app = Thread(target=run_http_server)
    server_app.start()
    
    server_socket = Thread(target=run_socket_server)
    server_socket.start()
