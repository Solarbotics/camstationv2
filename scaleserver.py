import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.gen
from tornado.options import define, options

import time
import multiprocessing
import serialProcess

define("port", default=8080, help="run on the given port", type=int)

clients = []


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print
        'new connection'
        clients.append(self)
        self.write_message("connected")

    def on_message(self, message):
        print
        'tornado received from client: %s' % message
        self.write_message('got it!')

    def on_close(self):
        print
        'connection closed'
        clients.remove(self)


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = tornado.web.Application(
        handlers=[
            (r"/", IndexHandler),
            (r"/ws", WebSocketHandler)
        ]
    )
    httpServer = tornado.httpserver.HTTPServer(app)
    httpServer.listen(options.port)
    print
    "Listening on port:", options.port
    mainLoop = tornado.ioloop.IOLoop.instance()
    mainLoop.start()