#!/usr/bin/env python3

# Logviewer
# Modified from: https://github.com/jizhang/logviewer
# Original by Ji ZHANG (zhangji87@gmail.com)
# Modifications by Stacy Olivas (kg7qin@arrl.net)

import time
import os.path
import os
import sys
import asyncio
import logging
import argparse
from collections import deque
from urllib.parse import urlparse, parse_qs
import ssl
import pathlib

import websockets
from ansi2html import Ansi2HTMLConverter

from jinja2 import Environment, FileSystemLoader

from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
from threading import Thread

NUM_LINES = 1000
HEARTBEAT_INTERVAL = 15 # seconds

# init
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
allowed_prefixes = []
conv = Ansi2HTMLConverter(inline=True)


async def view_log(websocket, path):

    logging.info('Connected, remote={}, path={}'.format(websocket.remote_address, path))

    try:
        try:
            parse_result = urlparse(path)
        except Exception:
            raise ValueError('Fail to parse URL')

        file_path = os.path.abspath(parse_result.path)
        allowed = False
        for prefix in allowed_prefixes:
            if file_path.startswith(prefix):
                allowed = True
                break
        if not allowed:
            raise ValueError('Forbidden')

        if not os.path.isfile(file_path):
            raise ValueError('Not found')

        query = parse_qs(parse_result.query)
        tail = query and query['tail'] and query['tail'][0] == '1'

        with open(file_path) as f:

            content = ''.join(deque(f, NUM_LINES))
            content = conv.convert(content, full=False)
            await websocket.send(content)

            if tail:
                last_heartbeat = time.time()
                while True:
                    content = f.read()
                    if content:
                        content = conv.convert(content, full=False)
                        await websocket.send(content)
                    else:
                        await asyncio.sleep(1)

                    # heartbeat
                    if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                        try:
                            await websocket.send('ping')
                            pong = await asyncio.wait_for(websocket.recv(), 5)
                            if pong != 'pong':
                                raise Exception()
                        except Exception:
                            raise Exception('Ping error')
                        else:
                            last_heartbeat = time.time()

            else:
                await websocket.close()

    except ValueError as e:
        try:
            await websocket.send('<font color="red"><strong>{}</strong></font>'.format(e))
            await websocket.close()
        except Exception:
            pass

        log_close(websocket, path, e)

    except Exception as e:
        log_close(websocket, path, e)

    else:
        log_close(websocket, path)


def log_close(websocket, path, exception=None):
    message = 'Closed, remote={}, path={}'.format(websocket.remote_address, path)
    if exception is not None:
        message += ', exception={}'.format(exception)
    logging.info(message)


async def serve(host: str, port: int, ssl_context):
    async with websockets.serve(view_log, host, port, ssl=ssl_context):
        await asyncio.Future()

#
# Only outputs the rendered logs.html file and /health endpoint for health checks
#
class MyHttpRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global websocksrvurl
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text")
            self.end_headers()
            curr_time = time.ctime()
            self.wfile.write(bytes(f'HEALTHY - {curr_time}\r\n', "utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
    
            environment = Environment(loader=FileSystemLoader("./"))
            template = environment.get_template("logs.html")
            self.wfile.write(bytes(template.render(serverurl=websocksrvurl, pagetitle=title, newline=newline), "utf-8"))


#
# webserver 
#
def webserver():
    global webhost, webport
    # Create an object of the above class
    handler_object = MyHttpRequestHandler

    my_server = socketserver.TCPServer((webhost, webport), handler_object)

    logging.info('Webserver started on {}:{}'.format(webhost, webport))

    # Start the web server
    my_server.serve_forever()


#
# websocker server
#
def main(srvhost, srvport, ssl_context):
    asyncio.run(serve(srvhost, srvport, ssl_context))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1', help='Websockets server IP')
    parser.add_argument('--port', type=int, default=8765, help='Websockers server port')
    parser.add_argument('--webhost', default='127.0.0.1', help='Webserver IP')
    parser.add_argument('--webport', type=int, default=8000, help ='Webserver port')

    try:
        if len(os.getenv('LOGSRVPREFIX')) < 1:
            pass
    except:
        parser.add_argument('--prefix', action='append', help='Allowed directories')

    try:
        if len(os.getenv('LOGSRV_WEBSOCKURL')) < 1:
            pass
    except:
        parser.add_argument('--websockurl', help='URL to connect to websock server')

    parser.add_argument('--ssl', default='<empty>', help='Specify filename of ssl certificate .pem file')
    parser.add_argument('--title', default='Web Logviewer', help='Title of HTML webpage to show in browser')
    parser.add_argument('--newline', action='store_true', default=False, help='Add <br> to beginning of each log line to be displayed')
    args = parser.parse_args()

    try:
        if len(os.getenv('LOGSRV_HOST')) < 1:
            host = args.host
        else:
            host = os.getenv('LOGSRV_HOST')
    except:
        host = '127.0.0.1'

    try:
        if len(os.getenv('LOGSRV_PORT')) < 1:
            port = args.port
        else:
            port = int(os.getenv('LOGSRV_PORT'))
    except:
        port = 8765

    try:
        if len(os.getenv('LOGSRV_WEBHOST')) < 1:
            webhost = args.webhost
        else:
            webhost = os.getenv('LOGSRV_WEBHOST')
    except:
        webhost = '127.0.0.1'

    try:
        if len(os.getenv('LOGSRV_WEBPORT')) < 1:
            webport = args.webport
        else:
            webport = int(os.getenv('LOGSRV_WEBPORT'))
    except:
        webport = 8765

    try:
        if len(os.getenv('LOGSRV_PREFIX')) < 1:
            prefix = args.prefix
        else:
           prefix = os.getenv('LOGSRV_PREFIX')
    except:
        logging.info('Error: Prefix not set!')
        sys.exit()

    try:
        if len(os.getenv('LOGSRV_WEBSOCKURL')) < 1:
            websocksrvurl = args.websockurl
        else:
            websocksrvurl = os.getenv('LOGSRV_WEBSOCKURL')
    except:
        logging.info('Error Websockurl not set!')
        sys.exit()

    try:
        if len(os.getenv('LOGSRV_SSL')) < 1:
            sslcert = args.ssl
        else:
            sslcert = os.getenv('LOGSRV_SSL')
    except:
        sslcert ='<empty>'
    
    try:
        if len(os.getenv('LOGSRV_TITLE')) < 1:
           title = args.title
        else:
            title = os.getenv('LOGSRV_TITLE')
    except:
        title = 'Web Logviewer'

    try:
        if len(os.getenv('LOGSRV_NEWLINE')) < 1:
            newline = args.newline
        else:
            newline = False
            if (os.getenv('LOGSRV_NEWLINE')) == '1':
                newline = True
    except:
        newline = False

    allowed_prefixes.extend(prefix)

    # Start webserver in a thread
    thread = Thread(target=webserver)
    thread.daemon = True
    thread.start()
    time.sleep(2)

    # display some startup information
    if newline == True:
        logging.info('[*] <br/> will prepended to log output')
    else:
        logging.info('[*] Newlines disabled')

    logging.info(f'[*] HTML page title: {title}')
    logging.info(f'[*] Allowed prefixes: {prefix}')

    # 
    # load ssl certificate 
    #
    if sslcert != "<empty>":
        logging.info(f"[*] SSL cert: {sslcert}")
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            localhost_pem = pathlib.Path(__file__).with_name(sslcert)
            ssl_context.load_cert_chain(localhost_pem)
        except:
            logging.info("[!] Invalid or no SSL certificate specified, running in insecure mode!")
            ssl_context=None
    else:
        logging.info('[!] SSL Disabled')

    # Start websockets log viewer server
    logging.info('Starting Websockets server')
    logging.info(f'Websock server URL: {websocksrvurl}')
    main(host, port, ssl_context)
