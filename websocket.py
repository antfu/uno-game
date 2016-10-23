# -*- coding: utf-8 -*-
# @Author: Anthony
# @Date:   2016-04-03 00:16:35
# @Last Modified by:   Anthony
# @Last Modified time: 2016-04-08 21:54:50

import json
import tornado.websocket
from room import rooms

class ws_player(tornado.websocket.WebSocketHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.room = None
        self.player = None
        self.name = None

    def open(self, room_name, player_name):
        self.name = player_name
        if rooms.has_room(room_name):
            self.room = rooms.get_room(room_name)
            self.player = self.room.connect(self.name,self)
            if not self.player:
                self.try_close()
        else:
            self.try_close()

    def on_close(self,*args,**kwargs):
        if not self.room is None:
            self.room.disconnect(self.name,self)

    def on_message(self, message):
        try:
            data = json.loads(message)
        except:
            self.send_json_message(error="Unexcepted format")
        else:
            self.handle_message(data)

    def try_close(self):
        if self.ws_connection is not None:
            self.close()

    def send_message(self,message):
        if self.ws_connection is not None:
            self.write_message(message)

    def send_json_message(self,dict_data=None,**items):
        self.send_message(json.dumps(dict_data or items))

    def check_origin(self, origin):
        # check orgin. TODO: Furher, learn more
        return True

    def handle_message(self, msg):
        if not isinstance(msg,dict): return
        if msg.get('action',None) is None: return

        if msg['action'] == 'chat':
            self.room.new_pipe().chat_msgs(self.player,msg.get('message',None)).boardcast()
        # Info Requests
        elif msg['action'] == 'scoreboard':
            self.room.new_pipe().scoreboard().messageto(self.player)
        elif msg['action'] == 'candidates':
            self.room.new_pipe().candidates().messageto(self.player)
        elif msg['action'] == 'ground':
            self.room.new_pipe().ground().messageto(self.player)
        elif msg['action'] == 'hand':
            self.room.new_pipe().hand(self.player).messageto(self.player)
        elif msg['action'] == 'gameplay':
            self.room.new_pipe().gameplay(self.player).messageto(self.player)
        elif msg['action'] == 'recover':
            self.room.new_pipe().recover(self.player).messageto(self.player)

        # Games
        elif msg['action'] == 'start':
            self.room.start()
        elif msg['action'] == 'play':
            if msg.get('card_index',None) is None: return
            self.player.play(msg['card_index'], msg.get('user_color',None))
        elif msg['action'] == 'drawone':
            self.player.drawone()
        elif msg['action'] == 'accept_punish':
            self.player.accept_punish()
        elif msg['action'] == 'auto':
            self.player.autoplay()
        elif msg['action'] == 'pass':
            self.player.pass_turn()
