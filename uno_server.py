# -*- coding: utf-8 -*-
# @Author: Anthony
# @Date:   2016-03-30 12:48:58
# @Last Modified by:   Anthony
# @Last Modified time: 2016-04-08 20:26:47

import sys
import json
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.options
import room
import websocket
from   configs.config   import configs
from room import rooms

class base_handler(tornado.web.RequestHandler):
    def get_template_namespace(self):
        ns = super(base_handler, self).get_template_namespace()
        ns.update({
            'root': configs.root
        })
        return ns

    def redirect(self,url):
        super().redirect(configs.root+url)

    def redirect_param(self,url,**params):
        if params:
            self.redirect(url+'?'+'&'.join(['%s=%s' % (k,v) for k,v in params.items()]))
        else:
            self.redirect(url)

class base_room_handler(base_handler):
    def get_room(self,room_name,player_name=None):
        if not rooms.has_room(room_name):
            if player_name is None:
                self.redirect_param('/create',room=room_name,msg='room_not_exist')
            else:
                self.redirect_param('/create',room=room_name,msg='room_not_exist',player=player_name)
            return False
        self.room = rooms.get_room(room_name)
        return self.room

class lobby_handler(base_handler):
    def get(self):
        self.render('lobby.html',rooms=rooms)

class create_handler(base_handler):
    def get(self,room_name=None):
        if room_name is None:
            self.render('create.html')
        else:
            if rooms.has_room(room_name):
                self.redirect_param('/room/'+room_name,msg='room_already_exist')
            else:
                r = rooms.create_room(room_name)
                if r:
                    self.redirect_param('/room/'+room_name)
                else:
                    self.redirect_param('/',room=room_name,error=repr(r))

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
            self.redirect_param('/',msg='room_close_successful')
        else:
            self.redirect_param('/',msg='room_close_failed')


class room_restart_handler(base_room_handler):
    def get(self,room_name):
        if not self.get_room(room_name): return
        # TODO
        self.redirect('/room/'+room_name)

class room_clear_handler(base_room_handler):
    def get(self,room_name):
        if not self.get_room(room_name): return
        self.room.clear_scoreboard()
        self.redirect('/room/'+room_name)

class player_handler(base_room_handler):
    def get(self,room_name,player_name):
        if not self.get_room(room_name): return
        p = self.room.join(player_name)
        if p:
            self.render('table.html',room=self.room,player=p,chat_root=configs.chat_root)
        else:
            self.redirect_param('/room/'+room_name,msg=repr(p))

class not_found_handler(base_room_handler):
    def get(self):
        self.render('404.html')

args = sys.argv
args.append("--log_file_prefix=logs/web.log")
tornado.options.parse_command_line()
app = tornado.web.Application(
    handlers=[
        (r'/',lobby_handler),
        (r'/create',create_handler),
        (r'/create/(\w+)',create_handler),
        (r'/room/(\w+)',room_handler),
        (r'/room/(\w+)/options',options_handler),
        (r'/room/(\w+)/close',room_close_handler),
        (r'/room/(\w+)/restart',room_restart_handler),
        (r'/room/(\w+)/clear',room_clear_handler),
        (r'/room/(\w+)/player/(\w+)',player_handler),
        (r'/room/(\w+)/player/(\w+)/ws',websocket.ws_player),
        (r'.*',not_found_handler)
    ],
    template_path='template',
    static_path='static',
    debug=True
)
http_server = tornado.httpserver.HTTPServer(app)
http_server.listen(configs.port)
tornado.ioloop.IOLoop.instance().start()