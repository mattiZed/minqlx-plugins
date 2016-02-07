# This is an extension plugin  for minqlx.
# Copyright (C) 2016 mattiZed (github) aka mattiZed (ql)

# You can redistribute it and/or modify it under the terms of the 
# GNU General Public License as published by the Free Software Foundation, 
# either version 3 of the License, or (at your option) any later version.

# You should have received a copy of the GNU General Public License
# along with minqlx. If not, see <http://www.gnu.org/licenses/>.

# Parts of this plugin were inspired by iou(onegirl)'s autospec plugin.
# Deciding who to put to spectators it goes a whole different way though:

# We keep a dictionary containing all players on the server as keys and their
# PLAYTIME as values. In this context, playtime means for how long the player
# was in red or blue team in an ACTIVE GAME - no matter for how long
# he was alive though!

# For now, the plugin warns that teams are uneven on event round_countdown and 
# slays or move to spectators the player who was in-game the shortest 
# on event round_start.

# I wrote a little timer module that can be used to start and stop timers.
# If a timer was stopped yet not cleared 
# (therefore you'd have to reinstantiate the object) 
# the modules' .start() method just resumes the timer.

# .elapsed() tells how many seconds have passed since the timer was
# _started_for_the_first_time_, no matter if it is paused or running.

# Please consider this a very early version and highly experimental. 
# I haven't tested it that much yet because testing these things is hard...

import minqlx
import datetime

class timer():
    def __init__(self, running=False):
        self._started = None
        self._running = False
        self._elapsed = 0
        if running:
            self.start()
    
    def start(self):
        if self._running:
            return
            
        self._started = datetime.datetime.now()
        self._running = True
        
    def stop(self):
        if not self._started or not self._running:
            return
        stopped = datetime.datetime.now()
        diff = stopped - self._started
        self._elapsed += diff.seconds
        self._running = False
    
    def elapsed(self):
        if self._running:
            now = datetime.datetime.now()
            diff = now - self._started
            self._elapsed += diff.seconds
            self._started = now
            return self._elapsed
        else:
            return self._elapsed

class uneventeams(minqlx.Plugin):
    def __init__(self):
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("game_end", self.handle_game_end)
        self.add_command("playertimes", self.cmd_playertimes, 2)
        
        # { steam_id : time_played }
        self._players = {}
        
        self.initialize()
        
        # Slay (0) or move to spectators (1) when teams are uneven
        self.set_cvar_once("qlx_unevenTeamsAction", "0")
        # Minimum amount of players in red + blue for uneventeams to work
        self.set_cvar_once("qlx_unevenTeamsMinPlayers", "2")
        
    def initialize(self):
        '''
            Equip all players with timers on plugin load.
        '''
        players = self.teams()
        
        for p in players["red"]:
            self._players[p.steam_id] = timer()
        for p in players["blue"]:
            self._players[p.steam_id] = timer()
        for p in players["spectator"]:
            self._players[p.steam_id] = timer()
    
    def handle_round_countdown(self, round_number):
        '''
            Check if teams are uneven and if so, warn the player with the 
            least amount of time played.
        '''
        min_players = self.get_cvar("qlx_unevenTeamsMinPlayers", int)
        
        teams = self.teams()
        
        if len(teams["red"]) == len(teams["blue"]):
            return
        if len(teams["red"] + teams["blue"]) < min_players:
            return
        
        if len(teams["red"]) > len(teams["blue"]):
            guy = self.player(self.find_lastjoined("red"))
        else:
            guy = self.player(self.find_lastjoined("blue"))
        self.msg("^1Uneven Teams^7 >> {}^7 joined last and should spectate".format(guy.name))
    
    def handle_round_start(self, round_number):
        '''
            Start (or resume) the timers for the players in RED and BLUE.
            Check also if we need to slay someone.
        '''
        min_players = self.get_cvar("qlx_unevenTeamsMinPlayers", int)
        action = self.get_cvar("qlx_unevenTeamsAction", int)
        
        teams = self.teams()
        
        for p in teams["red"]:
            self._players[p.steam_id].start()
        
        for p in teams["blue"]:
            self._players[p.steam_id].start()
        
        for p in self._players.keys():
            try: 
                self.player(p)
            except:
                del self._players[p]
        
        if len(teams["red"]) == len(teams["blue"]):
            return
        if len(teams["red"] + teams["blue"]) < min_players:
            return
        
        if len(teams["red"]) > len(teams["blue"]):
            guy = self.player(self.find_lastjoined("red"))
        else:
            guy = self.player(self.find_lastjoined("blue"))
        
        if action == 0:
            guy.health = 0
            self.msg("^1Uneven Teams^7 >> {}^7 was slain.".format(guy.name))
        if action == 1:
            guy.put("spectator")
            self.msg("^1Uneven Teams^7 >> {}^7 was moved to spectators.".format(guy.name))
        
    def handle_round_end(self, round_number):
        '''
            The round is over, stop the players' timers.
        '''
        teams = self.teams()
        
        for p in teams["red"] + teams["blue"]:
            self._players[p.steam_id].stop()
    
    def handle_game_end(self, data):
        '''
            The game has ended for any reason. Stop all timing.
        '''
        teams = self.teams()
        
        for p in teams["red"]:
            self._players[p.steam_id].stop()
        
        for p in teams["blue"]:
            self._players[p.steam_id].stop()
    
    def handle_team_switch(self, player, old_team, new_team):
        '''
            If a player joined spectators he cant gain playtime.
        '''
        if new_team == "spectator":
            self._players[player.steam_id].stop()
            
    def handle_player_disconnect(self, player, reason):
        if player.steam_id in self._players.keys():
            del self._players[player.steam_id]
    
    def handle_player_connect(self, player):
        '''
            Equip every new player with a timer instance.
        '''
        self._players[player.steam_id] = timer()
    
    def cmd_playertimes(self, player, msg, channel):
        # This one is mostly for debugging.
        teams = self.teams()
        red_msg = ""
        for p in teams["red"]:
            red_msg += "^7{}:^1 {}^7s ".format(p, self._players[p.steam_id].elapsed())
        
        blue_msg = ""
        for p in teams["blue"]:
            blue_msg += "^7{}:^4 {}^7s ".format(p, self._players[p.steam_id].elapsed())
            
        spec_msg = ""
        for p in teams["spectator"]:
            spec_msg += "^7{}:^7 {}^7s ".format(p, self._players[p.steam_id].elapsed())
        
        channel.reply(red_msg)
        channel.reply(blue_msg)
        channel.reply(spec_msg)
    
    def find_lastjoined(self, team):
        '''
            Find the player with the least amount of time played.
        '''
        teams = self.teams()
        if team == "red":
            players = teams["red"]
        else:
            players = teams["blue"]
            
        bigger_team = {}
        for p in players:
            bigger_team[p.steam_id] = self._players[p.steam_id].elapsed()
            
        namesbytime = sorted(bigger_team, key = lambda item: bigger_team[item])
        return namesbytime[0]
        
