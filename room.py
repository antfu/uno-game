# -*- coding: utf-8 -*-
# @Author: Anthony
# @Date:   2016-03-30 02:56:17
# @Last Modified by:   Anthony
# @Last Modified time: 2016-04-08 00:53:00

import uno
import json
import time
from   configs.config   import configs
from uno import default_rules
from utils import set_timeout
from utils import NoneGet as NG
from utils import name_prettify, name_normalize

default_options = {
    'visiable' : True,
    'allow_watch' : True,
    'protected' : False,
    'password' : None,
    'join_singleton' : False,
    'min_players' : 2,
    'max_players' : 10,
    'turn_timeout': 30
}


class RoomPlayer:
    def __init__(self,room,name):
        self.room = room
        self.name = name
        self.display_name = name_prettify(self.name)
        self.sockets = []
        self.game_player = None
        self.score = 0
        self.prev_score = None
        self.wins = 0
        self.played = 0
        self.is_ingame = False
        self.timer = None

        self.on_disconnect_all = lambda is_turn: None

    @property
    def cards(self):
        if self.is_ingame:
            return len(self.game_player.hand)
        else:
            return 0

    @property
    def hand(self):
        if self.is_ingame:
            return self.game_player.hand
        else:
            return None

    @property
    def is_turn(self):
        if self.game_player and self.room.game:
            return self.game_player == self.room.game.current_player
        else:
            return None

    @property
    def is_online(self):
        return len(self.sockets)

    def autoplay(self):
        if self.room and self.room.game and self.game_player:
            self.game_player.autoplay()
    def drawone(self):
        if self.game_player:
            self.game_player.drawone()
    def accept_punish(self):
        if self.game_player:
            if self.game_player.accept_punish():
                self._user_action()
    def pass_turn(self):
        if self.game_player:
            if self.game_player.pass_turn():
                self._user_action()
    def play(self,card,color=None):
        if self.game_player:
            if self.game_player.play(card,color):
                self._user_action()

    def _user_action(self):
        self.remove_timer()

    def set_timer(self, sec):
        self.remove_timer()
        self.timer = set_timeout(self.autoplay,sec)

    def remove_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _on_disconnect_all(self):
        self.room.new_pipe().player_left(self).boardcast()
        if self.is_turn: self.set_timer(5)
        self.on_disconnect_all(self.is_turn)
        # If all the player is disconnected,
        # over the game
        if not self.room.players_online:
            self.room.end()

    def send_message(self,action='ping',**message):
        message['action'] = action
        for ws in self.sockets:
            ws.send_json_message(message)

    def send_raw_message(self,message):
        for ws in self.sockets:
            ws.send_message(message)

    def connect(self,ws):
        self.sockets.append(ws)
        self.room.bc_player_join(self)
        self.room.new_pipe().scoreboard().messageto(self)

    def disconnect(self,ws):
        try:
            self.sockets.remove(ws)
        except:
            return False
        else:
            # autoplay when a player lost he's all connections
            if not self.is_online:
                self._on_disconnect_all()
            return True

    def bind_game_player(self,game_player):
        self.game_player = game_player
        self.game_player.on_my_turn = lambda: self.on_my_turn()
        self.game_player.on_change = lambda: self.on_change()
        self.is_ingame = True

    def add_score(self):
        if self.game_player:
            if self.game_player.score > 0:
                self.wins += 1
            self.played += 1
            self.score += self.game_player.score
            self.prev_score = self.game_player.score

    def clear_score(self):
        self.played = 0
        self.wins = 0
        self.score = 0
        self.prev_score = 0

    def on_change(self):
        self.room.new_pipe().hand(self).messageto(self)

    def on_others_turn(self):
        self.remove_timer()

    def on_my_turn(self):
        if not self.is_online:
            # If player is disconnected when it's his/her turn,
            # set an autoplay-timer for 5sec
            self.set_timer(5)
        else:
            # Set an autoplay-timer to limit player's turn time
            if self.room.options['turn_timeout'] > 0:
                self.set_timer(self.room.options['turn_timeout'])
            self.room.new_pipe().myturn(self).messageto(self)

    def on_gameover(self):
        self.is_ingame = False
        self.game_player = None

class Room:
    def __init__(self,name,options=None,rules=None):
        self.name=name
        self.display_name = name_prettify(self.name)
        self.options=dict(default_options)
        self.rules=dict(default_rules)
        if not options is None:
            self.options.update(options)
        if not rules is None:
            self.rules.update(rules)
        self.game_players=[]
        self.room_players={}
        self.games_played=0
        self.state = 0
        self.game = None

    @property
    def players(self):
        return self.room_players.values()
    @property
    def players_online(self):
        return [x for x in self.players if x.is_online]
    @property
    def players_ingame(self):
        return [x for x in self.players if x.is_ingame]
    @property
    def onlines(self):
        return len(self.players_online)
    @property
    def ingames(self):
        return len(self.players_ingame)
    @property
    def visiable(self):
        return self.options['visiable']
    @property
    def min_players(self):
        return self.options['min_players']
    @property
    def max_players(self):
        return self.options['max_players']
    @property
    def state_str(self):
        if self.state == 0:
            if self.onlines == 0:
                return 'Empty'
            elif self.onlines < self.min_players:
                return 'Matching'
            elif self.onlines >= self.max_players:
                return 'Full'
            else:
                return 'Ready'
        else:
            return ['Ready','Gaming','Disabled'][self.state]

    def new_pipe(self):
        return MessagePipe(self)

    def get_player(self,name):
        return self.room_players.get(name_normalize(name),None)

    def set_rule(self,key,value):
        self.rules[key] = value

    def get_players_str(self,amount=None,filter=None):
        if amount == 0: return ''
        # Select type of players to be displayed
        if filter == 'online':
            players = self.players_online
        elif filter == 'ingame':
            players = self.players_ingame
        else:
            players = self.players
        # Select last parts of players
        tail = ''
        if not amount is None and amount < len(players):
            players = players[-amount:]
            tail = ' ...'
        # Stringify
        return ', '.join([x.display_name for x in players]) + tail


    #################################
    @property
    def game_ready(self):
        if self.options['min_players'] > self.onlines:
            return False
        if self.options['max_players'] < self.onlines:
            return False
        if self.state != 0:
            return False
        return True

    def clear_scoreboard(self):
        for p in self.room_players:
            p.clear_score()
        self.new_pipe().scoreboard().boardcast()

    def start(self,force=False):
        if force:
            if len(self.players_online) < 2:
                return False
        else:
            if not self.game_ready:
                return False
        del(self.game_players)
        del(self.game)
        self.game_players=[]
        self.game = uno.Game(self.rules)
        for p in self.players_online:
            # join game only went user connected
            gp = self.game.add_player(p.name)
            p.bind_game_player(gp)
            self.game_players.append(gp)
        self.game.on_turn = lambda x: self.on_turn(x)
        self.game.on_player_uno = lambda x: self.on_player_uno(x)
        self.game.on_gameover = lambda x: self.on_gameover(x)
        self.game.on_card_played = lambda x: self.bc_card_played(x)
        self.state = 1
        self.new_pipe().gamestart().boardcast()
        self.game.start()


    def joinable(self,name):
        if name in self.room_players.keys():
            # when player is online, check if allow to build another connection
            if self.room_players[name].is_online:
                if self.options['join_singleton']:
                    return NG('player_already_joined')
                else:
                    return True
        if len(self.players_online) >= self.options['max_players']:
            return NG('room_full')
        return True

    def join(self,name):
        joinable = self.joinable(name)
        if joinable:
            p = self.get_player(name)
            if p is None:
                p = RoomPlayer(self,name)
                self.room_players[name] = p
            return p
        return joinable

    def leave(self,name):
        pass

    def connect(self,name,ws):
        p = self.get_player(name)
        if not p: return False
        p.connect(ws)
        return p

    def disconnect(self,name,ws):
        p = self.get_player(name)
        if not p: return False
        return p.disconnect(ws)

    def shutdown(self):
        self.boardcast('kick')
        self.room_players={}
        self.end()

    def end(self):
        self.state = 0
        self.game = None
        self.game_players=[]
        self.games_played = 0
        self.clear_scoreboard()


    ################################

    def boardcast(self,action='ping',**message):
        for player in self.players:
            player.send_message(action,**message)

    ################################

    def on_turn(self,x):
        for player in self.players_ingame:
            player.on_others_turn()
        self.new_pipe().candidates().turns().boardcast()

    def on_player_uno(self,x):
        pass

    def on_gameover(self,x):
        self.state = 0
        for p in self.players:
            p.add_score()
        self.games_played += 1
        self.new_pipe().gameover(x).scoreboard().boardcast()
        for p in self.players:
            p.on_gameover()
        self.end()

    def on_player_changed(self,player):
        pass

    ################################
    def bc_sys_msg(self,message):
        self.new_pipe().system_msgs(message).boardcast()

    def bc_card_played(self,card):
        self.new_pipe().card_played(card).boardcast()

    def bc_info(self):
        self.new_pipe().game_infos().boardcast()

    def bc_player_join(self,player):
        self.new_pipe().player_joined(player).boardcast()

class MessagePipe:
    def __init__(self,room):
        self.room = room
        self.data = {}
        self.json_cache = None

    @property
    def json(self):
        if not self.json_cache:
            self.json_cache = json.dumps(self.data)
        return self.json_cache

    @property
    def dict(self):
        return self.data

    def append(self,**msg):
        self.data.update(msg)
        self.json_cache = None
        return self

    def boardcast(self):
        for player in self.room.players:
            player.send_raw_message(self.json)
        return self

    def messageto(self,player):
        player.send_raw_message(self.json)
        return self

    def list_append(self,key,value):
        if value is None: return self
        orginal = self.data.get(key,[])
        orginal.append(value)
        data = {key:orginal}
        return self.append(**data)

    # ---- Room Data Append ----
    ## Should be Boardcast or MessageTo
    def ground(self):
        if self.room.game:
            return self.append(ground=[repr(c) for c in self.room.game.get_ground()])
        else:
            return self.append(ground=[])

    def card_played(self,card):
        return self.append(card_played=repr(card))

    def candidates(self):
        return self.append(
            candidates=[name_prettify(x.name)+':'+str(len(x.hand))
                        for x in self.room.game.candidates])

    def scoreboard(self):
        scoreboard = [(p.display_name,
                       p.prev_score or 0,
                       str(p.wins or 0) + '/' + str(p.played or 0),
                       p.score or 0)
                        for p in self.room.players if p.played]
        return self.append(games_played=self.room.games_played,
                           scoreboard=sorted(scoreboard,key=lambda x:x[3],reverse=True))

    def gameover_scoreboard(self):
        gameover_scoreboard = [(p.display_name,p.cards or 0,p.prev_score or 0,p.score or 0)
                                for p in self.room.players_ingame]
        return self.append(gameover_scoreboard=sorted(gameover_scoreboard,key=lambda x:x[1]))

    def system_msgs(self,message):
        return self.list_append('system_msgs',message)

    def chat_msgs(self,player,message):
        return self.list_append('chat_msgs',(player.display_name,message))

    def players_online_list(self):
        return self.append(players_online_list=self.room.get_players_str(None,'online') or 'Nobody')

    def player_joined(self,player):
        return self.append(player_joined=player.display_name).game_ready().players_online_list()

    def player_left(self,player):
        return self.append(player_left=player.display_name).game_ready().players_online_list()

    def game_ready(self):
        return self.append(game_ready=self.room.game_ready,
                           game_ready_players=len(self.room.players_online),
                           game_state_str=self.room.state_str)

    def turns(self):
        return self.append(turns=self.room.game.turns,
                           prev_color=self.room.game.previous_color
                           ).countdown(self.room.options['turn_timeout'])

    def game_infos(self):
        return self.append(game_infos={})

    def countdown(self,num):
        return self.append(countdown=num)

    def gameover(self,winner):
        return self.append(gameover=True,winner=name_prettify(winner.name)).gameover_scoreboard().game_ready()

    def gamestart(self):
        return self.append(gamestart=True).game_ready()

    ## Should only be MessageTo
    def hand(self,player):
        if player.hand:
            return self.append(hand=[repr(c) for c in player.hand])
        else:
            return self

    def myturn(self,player):
        if player.is_turn:
            return self.append(myturn=True,
                               punish_stack=self.room.game.punishment[0],
                               punish_level=self.room.game.punishment[1],
                               drawable=player.game_player.drawable)
        else:
            return self

    def gameplay(self,player):
        return self.hand(player).ground().candidates().turns().myturn(player)

    def recover(self,player):
        return self.game_infos().game_ready().gameplay(player)


class RoomManager:
    def __init__(self):
        self.rooms = {}
        self.max_limit = configs.room_max_limit
        for name in configs.default_rooms:
            self.create_room(name)

    @property
    def public_rooms(self):
        return [x for x in self.rooms.values() if x.visiable]

    def has_room(self,room_name):
        return room_name in self.rooms.keys()

    def get_room(self,room_name):
        if self.has_room(room_name):
            return self.rooms.get(room_name,None)
        else:
            return self.create_room(room_name)

    def create_room(self,room_name,options=None,rules=None):
        if self.has_room(room_name):
            return NG('room_alreay_exist','Room alreay exist.')
        if len(self.rooms.values()) >= self.max_limit:
            return NG('lobby_full','Rooms\' max limit reached.')
        new_room = Room(room_name,options,rules)
        self.rooms[room_name] = new_room
        return new_room

    def close_room(self,room_name):
        if not self.has_room(room_name):
            return False
        room = self.rooms.get(room_name,None)
        room.shutdown()
        del(self.rooms[room_name])
        return True

    def clean_rooms(self,expired_time = 600):
        expired_rooms_id = []
        for k in self.rooms.keys():
            r = self.rooms[k]
            if time.time() - r.game.active_time > expired_time:
                expired_rooms_id.append(k)
        for k in expired_rooms_id:
            self.rooms[k].end()
            del(self.rooms[k])

rooms = RoomManager()