# -*- coding: utf-8 -*-
# @Author: Anthony
# @Date:   2016-03-30 12:48:58
# @Last Modified by:   Anthony
# @Last Modified time: 2016-04-04 15:28:15

import json
import tornado.web
import tornado.httpserver
import tornado.ioloop
import room
import websocket
from   configs.config   import configs
from room import rooms

class base_room_handler(tornado.web.RequestHandler):
    def get_room(self,room_name,player_name=None):
        if not rooms.has_room(room_name):
            if player_name is None:
                self.redirect('/create?room=%s&msg=room_not_exist' % room_name)
            else:
                self.redirect('/create?room=%s&player%s&msg=room_not_exist' % (room_name,player_name))
            return False
        self.room = rooms.get_room(room_name)
        return self.room

class lobby_handler(tornado.web.RequestHandler):
    def get(self):
        self.render('lobby.html',rooms=rooms)

class create_handler(tornado.web.RequestHandler):
    def get(self,room_name=None):
        if room_name is None:
            self.render('create.html')
        else:
            if rooms.has_room(room_name):
                self.redirect('/room/%s?msg=room_already_exist' % room_name)
            else:
                r = rooms.create_room(room_name)
                if r:
                    self.redirect('/room/%s?msg=create_success' % room_name)
                else:
                    self.redirect('/?room=%s&error=%s' % (room_name,repr(r)))

class room_handler(base_room_handler):
    def get(self,room_name):
        if not self.get_room(room_name): return
        self.render('join.html',room=self.room)

class options_handler(base_room_handler):
    def get(self,room_name):
        if not self.get_room(room_name): return
        self.render('options.html',room=self.room)

class room_close_handler(base_room_handler):
    def get(self,room_name):
        result = rooms.close_room(room_name)
        if result:
            self.redirect('/?msg=room_close_successful')
        else:
            self.redirect('/?msg=room_close_failed')


class room_restart_handler(base_room_handler):
    def get(self,room_name):
        if not self.get_room(room_name): return
        # TODO
        self.redirect('/room/%s' % room_name)


class player_handler(base_room_handler):
    def get(self,room_name,player_name):
        if not self.get_room(room_name): return
        p = self.room.join(player_name)
        if p:
            self.render('table.html',room=self.room,player=p)
        else:
            self.redirect('/room/%s?msg=%s' % (room_name,repr(p)))

app = tornado.web.Application(
    handlers=[
        (r'/',lobby_handler),
        (r'/create',create_handler),
        (r'/create/(\w+)',create_handler),
        (r'/room/(\w+)',room_handler),
        (r'/room/(\w+)/options',options_handler),
        (r'/room/(\w+)/close',room_close_handler),
        (r'/room/(\w+)/restart',room_restart_handler),
        (r'/room/(\w+)/player/(\w+)',player_handler),
        (r'/room/(\w+)/player/(\w+)/ws',websocket.websocket_handler)
    ],
    template_path='template',
    static_path='static',
    debug=True
)
http_server = tornado.httpserver.HTTPServer(app)
http_server.listen(configs.port)
tornado.ioloop.IOLoop.instance().start()