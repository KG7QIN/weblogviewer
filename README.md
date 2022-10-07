Modified from: https://github.com/jizhang/logviewer
--

# Introduction

Dockerized version of the logfile viewer presented by Ji ZHANG in their blog https://shzhangji.com/blog/2017/07/15/log-tailer-with-websocket-and-python/

This version has been modified to:
* Work in Dockerized environments
* Uses Jinja2 templating to allow for the websocket (server.py) to be specified
* Can work with SSL (wss://) for websocket server
* Uses envrionment variables in docker-compose.yml files for configuration
* The log file's line are properly word wrapped to keep them from going off screen
* The webserver and websockets servers are combined so only one file is needed
* Only the .html file that is rendered by the jinja2 templating engine is served regardless of what is requested

While this is not the most ideal way to do this, it works and was an exercise in how to improve this basic tutorial on websocks for a specific application

I use this with Cloudflare's Zero Trust to view the logs of a docker-mailserver install.

Note:  This can be used in a docker container or stand alone.  Both environment varilables and command line swtiches can be used, but environment variables
will override the command line switches.

--

## Environment Variables
The following environment variables are available for use with Docker/docker-compose

* LOGSRV_HOST       - Websocket server hostname/IP address
* LOGSRV_PORT       - Websocket server port
* LOGSRV_WEBHOST    - Webserver hostname/IP address
* LOGSRV_WEBPORT    - Webserver port
* LOGSRV_PREFIX     - Websocket server logs prefix
* LOGSRV_SSL        - SSL certificate in .pem format
* LOGSRV_WEBSOCKURL - URL of Websocket server (ws:// and wss:// supported with SSL cert).  Used by HTML file to connect to server.
* LOGSRV_NEWLINE    - Add a newline before each log line printed (0-no/1-yes)
* LOGSRV_TITLE      - HTML webpage title

## Command Line Switches
The following command line swtiches are available for use as well

* --host            - Websocket server hostname/IP address
* --port            - Websocker server port
* --webhost         - Webserver hostname/IP address
* --webport         - Webserver port
* --prefix          - Websocket server prefix
* --websockurl      - URL of Websocket server.  (ws:// and wss:// supported with SSL cert).  Use by HTML file to connect to server.
* --ssl             - SSL certificate in .pem format
* --title           - HTML webpage title
* --newline         - Add by itself to add a newline before each log line printed



