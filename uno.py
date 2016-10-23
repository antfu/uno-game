# -*- coding: utf-8 -*-
# @Author: Anthony
# @Date:   2016-03-29 20:08:27
# @Last Modified by:   Anthony
# @Last Modified time: 2016-04-03 01:51:49

import random
import time
import threading

color_full = ['','Red','Yellow','Blue','Green']
color_repr = ['S','R','Y','B','G']
num_full = ['Zero','One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Draw Two','Reverse','Skip','Draw Four','Wild','Blank']
num_repr = ['0','1','2','3','4','5','6','7','8','9','D2','R','S','D4','W','B']
index_d2 = 10
index_r = 11
index_s = 12
index_d4 = 13
index_w = 14
index_b = 15
default_rules = {
    'cards_dealt' : 7, #done
    'special_last_punish' : True, # done
    'instant_gameover': True,
    'draw_n_stackable': True, # done
    'break_in': False,
    'blank_cards': 0,
    'blank_cards_text': []
}

class Card:
    def __init__(self,color,num):
        self.color = color
        self.num = num
        self.draw = 0
        if num == index_d2:
            self.draw = 2
        if num == index_d4:
            self.draw = 4

    def __repr__(self):
        return color_repr[self.color] + num_repr[self.num]

    def __str__(self):
        return (color_full[self.color] + ' ' + num_full[self.num]).strip()

    @property
    def is_special(self):
        return self.num > 9


class BlankCard(Card):
    def __init__(self,text):
        super().__init__(0,index_b)
        self.text = text

    def __repr__(self):
        return 'SB'

    def __str__(self):
        return 'Blank:\{{}\}'.format(self.text)

class Deck:
    def __init__(self,shuffle=True):
        self.deck = []
        self.deck_amount = 0
        self._new()
        if shuffle:
            self._shuffle()

    def __repr__(self):
        return 'Uno Deck ({})'.format(len(self.deck))

    def _new(self):
        # Create a new deck of cards
        self.deck += [ Card(c,n)
                            for c in range(1,5)
                            for n in list(range(1,10)) * 2 + [0] ] + \
                     [ Card(c,f)
                            for c in range(1,5)
                            for f in list(range(10,13)) * 2 ] + \
                     [ Card(0,f)
                            for f in [13,14] * 4]
        self.deck_amount += 1

    def _shuffle(self):
        random.shuffle(self.deck)

    def pop(self):
        if not len(self.deck):
            self._new()
            self._shuffle()
        return self.deck.pop()

class Player:
    def __init__(self,game,name,robot=False,robot_delay=0):
        self.game = game
        self.name = name.capitalize()
        self.id = None
        self.hand = []
        self.drawable = False
        self.myturn = False
        self.on_my_turn = lambda: None
        self.on_change = lambda: None
        self.on_uno = lambda: None
        self.buffer = []
        self.robot = robot
        self.robot_delay = robot_delay
        self.score = 0

    @property
    def handscore(self):
        score = 0
        for c in self.hand:
            if not c.is_special:
                score += c.num
            elif c.color == 0:
                score += 40
            else:
                score += 20
        return score


    def robot_delay_thread(self):
        if self.robot_delay:
            th = threading.Thread(target=self.robot_auto)
            th.start()
        else:
            self.robot_auto()

    def robot_auto(self):
        time.sleep(self.robot_delay)
        self.autoplay()

    def on_turn(self):
        if self.robot:
            self.robot_delay_thread()
        else:
            self.on_my_turn()

    def drawone(self):
        if not self.myturn: return False
        if self.drawable:
            self.game.draw_to_player(self.id,1)
            self.drawable = False
            if not self.robot:
                self.on_my_turn()
            return True
        else:
            return False

    def play(self, index, user_color=None):
        index = int(index)
        if not self.game.playing: return False
        if not self.myturn: return False
        if index > len(self.hand) - 1: return False
        return self.game.play(self,self.hand[index],user_color)

    def autoplay(self):
        if not self.game.playing: return False
        if not self.myturn: return False
        playables = []
        # Pick out all playable cards
        for i in range(len(self.hand)):
            if self.game.playable(self.hand[i]):
                playables.append(i)
        if len(playables):
            return self.play(random.choice(playables))
        else:
            # No card is playable
            if self.drawone():
                return self.autoplay()
            elif self.pass_turn():
                return True
            else:
                return self.accept_punish()

    def accept_punish(self):
        if not self.myturn: return False
        return self.game.punish(self.id)

    def pass_turn(self):
        if not self.myturn: return False
        if self.drawable: return False
        if self.game.has_punishment: return False
        self.game.turn()
        return True

    def confirm(self):
        if not self.myturn: return False
        if self.drawable: return False
        if self.game.has_punishment: return False
        self.game.turn()
        return True

    def __repr__(self):
        return '{}:{}'.format(self.name,len(self.hand))

    def __str__(self):
        return self.name

class Game:
    def __init__(self, rules = None):
        self.rules = dict(default_rules)
        if not rules is None:
            self.rules.update(rules)

        self.players = []
        self.playing = False

        # Callbacks
        self.on_turn = lambda x: None
        self.on_player_uno = lambda x: None
        self.on_gameover = lambda x: None
        self.on_card_played = lambda x: None

        self.deck = Deck()
        self.ground = []
        self.current_player_id = 0
        self.turns = 0
        self.player_count = 0
        self.turn_order = 1
        self.punishment = [0,0]
        self.previous = None

    def __repr__(self):
        return 'Uno Game | Players:{} | Turn:{} | Prev:{} | Punish:{} | Order:{}' \
            .format(len(self.players),self.turns,self.previous,self.punishment,self.turn_order)

    @property
    def candidates(self):
        cur = self.current_player_id
        p1 = self.get_next_id(cur,turn_order=-self.turn_order)
        p2 = self.get_next_id(p1,turn_order=-self.turn_order)
        n1 = self.get_next_id(cur)
        n2 = self.get_next_id(n1)
        return [
            self.players[p2],
            self.players[p1],
            self.players[cur],
            self.players[n1],
            self.players[n2]]

    def _gameover(self,winner):
        self.playing = False
        winnerscore = 0
        for p in self.players:
            s = p.handscore
            winnerscore += s
            p.score -= s
        winner.score += winnerscore
        self.on_gameover(winner)

    def add_player(self,name,robot=False,delay=0):
        p = Player(self,name,robot,delay)
        self.players.append(p)
        return p

    def remove_player(self,player):
        try: self.players.remove(player)
        except: return False
        else: return True

    def print_out(self):
        print(repr(self))
        print('-'*70)
        print('Ground','\t','({})'.format(len(self.ground)),self.get_ground())
        print('-'*70)
        for p in self.players:
            print(p.name,'\t','({})'.format(len(p.hand)),p.hand,
                  'UNO' if len(p.hand) == 1 else '',
                  '<' if p.id == self.current_player_id else '')

    def print_scoreboard(self):
        print('Scoreboard')
        print('-'*70)
        for p in sorted(self.players,key=lambda p:p.score):
            print(p.name,'\t',p.score)

    @property
    def current_player(self):
        if not self.current_player_id is None:
            return self.players[self.current_player_id]
        return None

    @property
    def has_punishment(self):
        return self.punishment[0] != 0

    @property
    def previous_color(self):
        if self.previous:
            return self.previous.color
        else:
            return 0

    def get_next_id(self,current_id=None,many=1,turn_order=None):
        if current_id is None:
            current_id = self.current_player_id
        if turn_order is None:
            turn_order = self.turn_order
        next_id = current_id + turn_order
        if next_id >= self.player_count:
            next_id = 0
        if next_id < 0:
            next_id = self.player_count - 1
        if many <= 1:
            return next_id
        else:
            return self.get_next_id(next_id,many - 1)

    def start(self):
        if len(self.players) < 2:
            return False
        else:
            self.deck = Deck()
            self.ground = []
            self.turns = 0
            self.turn_order = 1
            self.punishment = [0,0]
            self.previous = None
            self.player_count = len(self.players)
            self.order = 1

            random.shuffle(self.players)
            self.playing = True
            for i in range(len(self.players)):
                self.players[i].id = i
                self.players[i].hand = []
                self.draw_to_player(i,self.rules['cards_dealt'])

            while True:
                card = self.deck.pop()
                self.ground.append(card)
                self.on_card_played(card)
                self.previous = card
                if not card.is_special:
                    break;
            self.turn(0)
            return True

    def turn(self,player_id=None):
        ''' Set next turn to a player '''
        if not self.playing: return False
        # If the player if is not specified, switch to next player
        if player_id is None:
            player_id = self.get_next_id()
        prev_player = self.current_player
        if prev_player:
            # Disable Drawone flag of previous player
            prev_player.drawable = False
            # End previous player's turn
            prev_player.myturn = False
        # Set current player
        self.current_player_id = player_id
        curr_player = self.current_player
        # Enable Drawone flag if there is no punishment
        if not self.has_punishment:
            curr_player.drawable = True
        # Start current player's turn
        curr_player.myturn = True
        # Record
        self.turns += 1
        # Notification
        self.on_turn(self.current_player)
        self.current_player.on_turn()

    def draw_to_player(self,player_id,amount=1):
        if not self.playing: return False
        player = self.players[player_id]
        for i in range(amount):
            player.hand.append(self.deck.pop())
        player.on_change()
        return True

    def get_ground(self,amount=5):
        return self.ground[-amount:]

    def punish(self,player_id):
        ''' Take the punishment '''
        if not self.playing: return False
        if not self.has_punishment:
            return False
        self.draw_to_player(player_id,self.punishment[0])
        self.punishment = [0,0]
        self.turn()
        return True

    def playable(self,card):
        ''' Check if the card is playable '''
        if not self.playing: return False
        if not(not self.previous
               or card.color == 0
               or card.color == self.previous.color
               or card.num == self.previous.num):
            return False
        if self.has_punishment:
            if self.rules['draw_n_stackable']:
                # When there is a punishment, player can only allowed to play
                # the "Draw" card which is not weak than the previous one
                if self.punishment[1] > card.draw:
                    return False
            else:
                return False
        return True

    def play(self,player,card,user_color=None):
        ''' Play a card '''
        if not self.playing: return False
        if not self.playable(card):return False
        # Add the card to ground
        self.ground.append(card)
        # Get previous color/num
        color = card.color or user_color or random.choice([1,2,3,4])
        num = card.num
        next_id = self.get_next_id()

        # Card Functions
        if card.num == index_s or (card.num == index_r and self.player_count == 2):
            # SKIP
            next_id = self.get_next_id(many=2)
        elif card.num == index_r:
            # REVERSE
            self.turn_order = -self.turn_order
            next_id = self.get_next_id()
        elif card.num == index_d2 or card.num == index_d4:
            # DRAW 2/4
            self.punishment[0] += card.draw
            self.punishment[1] = card.draw

        if (self.rules['special_last_punish']
                and len(player.hand) == 1
                and card.is_special):
            # Punish when played special card as his/her last card
            self.draw_to_player(self.current_player_id,2)
        # Record
        player.hand.remove(card)
        player.on_change()
        self.previous = Card(color,num)
        self.on_card_played(card)
        self.turn(next_id)
        if len(player.hand) == 1:
            self.on_player_uno(player)
        if len(player.hand) == 0:
            self._gameover(player)
        return True
