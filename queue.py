# Copyright (C) mattiZed (github) aka mattiZed (ql)

# This is a queue plugin written for Mino's Quake Live Server Mod minqlx
# Some parts of it were inspired by the original queueinfo plugin which was
# written by WalkerX (github) for the old minqlbot.

# The plugin basically shows for how long people have been waiting in specator
# mode. If a player joins a team, the name is kept for three minutes (so admins
# can track players that dont respect the queue) in the list but now displayed
# with an asterisk to show that the player has left the queue and will soon be
# removed.

# The plugin also features an AFK list, to which players can 
# subscribe/unsubscribe to.

import minqlx
import datetime
import time

_tag_key = "minqlx:players:{}:clantag"

class queue(minqlx.Plugin):
    def __init__(self):
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("set_configstring", self.handle_configstring)
        self.add_command(("q", "queue"), self.cmd_lq)
        self.add_command("afk", self.cmd_afk)
        self.add_command("here", self.cmd_playing)
        
        self._queue = []
        self._afk   = []
        self.initialize()
        
        # Minimum time to play before a player gets removed from the queue (3m)
        self.set_cvar_once("qlx_queueRemPendingTime", "180")
        self.set_cvar_once("qlx_queueSetAfkPermission", "2")
        self.set_cvar_once("qlx_queueAFKTag", "^3AFK")
    
    def initialize(self):
        '''Puts spectators into queue when the plugin is loaded.'''
        specs = self.teams()["spectator"]
        for spec in specs:
            self.add(spec)
            time.sleep(0.01)
    
    ## Basic List Handling (Queue and AFK)
    def add(self, player, pos=-1):
        '''Safely adds players to the queue'''
        slot = {"name": player.name, "player" : player, "joinTime" : datetime.datetime.now()}
        if pos == -1:
            self._queue.append(slot)
        else:
            self._queue.insert(pos, slot)
    
    def rem(self, player):
        '''Safely removes players from the queue'''
        for item in self._queue:
            if item["player"] == player:
                self._queue.remove(item)
    
    def remAFK(self, player):
        '''Safely removes players from afk list'''
        for item in self._afk:
            if item["player"] == player:
                self._afk.remove(item)
    
    def inqueue(self, player):
        '''Returns True if player is in queue'''
        for item in self._queue:
            if item["player"] == player:
                return True
        return False
    
    def inafk(self, player):
        '''Returns True if player is in AFK'''
        for item in self._afk:
            if item["player"] == player:
                return True
        return False
    
    def clLists(self):
        '''Testing showed that sometimes players remain in the queue even 
        if they left the server long time ago. I built this to clean the lists.
        '''
        players = self.teams()["spectator"] + self.teams()["red"] + self.teams()["blue"]
        for pl in self._queue:
            if pl["player"] not in players:
                self.rem(pl["player"])
                
        for pl in self._afk:
            if pl["player"] not in players:
                self.remAFK(pl["player"])
    
    ## Queue Removal Handling
    def setRemPending(self, player):
        '''Set pending removal'''
        for item in self._queue:
            if item["player"] == player:
                item["RemPending"] = True
                item["RemPendingTime"] = datetime.datetime.now()
    
    def clRemPending(self, player):
        '''Clear pending removal'''
        for item in self._queue:
            if item["player"] == player:
                if "RemPending" in item.keys():
                    del item["RemPending"]
                    del item["RemPendingTime"]
    
    def isRemPending(self, player):
        '''Returns True if player is pending for removal from the queue'''
        for item in self._queue:
            if item["player"] == player:
                if "RemPending" in item.keys():
                    return True
                else:
                    return False
    
    def RemPending(self):
        '''Removes players from the queue when they are flagged for removal'''
        qcopy = self._queue.copy()
        for item in qcopy:
            if "RemPending" in item.keys():
                delta = datetime.datetime.now() - item["RemPendingTime"]
                if delta.seconds > self.get_cvar("qlx_queueRemPendingTime", int):
                    self.rem(item["player"])
    
    ## AFK Handling
    def setAFK(self, player):
        '''Returns True if player's state could be set to AFK'''
        if self.isRemPending(player):
            return False
        for i in range(len(self._queue)):
            if self._queue[i]["player"] == player:
                self._afk.append(self._queue.pop( i ))
                return True
        return False
    
    def setPlaying(self, player):
        '''Returns True if player's state could be set to AVAILABLE'''
        for i in range(len(self._afk)):
            if self._afk[i]["player"] == player:
                self._queue.append(self._afk.pop( i ))
                return True
        return False
    
    @minqlx.next_frame
    def setAFKTag(self, player):
        '''Sets the player's clantag to AFK'''
        player.clan = self.get_cvar("qlx_queueAFKTag")
    
    @minqlx.next_frame
    def clAFKTag(self, player):
        '''Sets player's clantag again if there was any'''
        tag_key = _tag_key.format(player.steam_id)
        tag = ""
        if tag_key in self.db:
            tag = self.db[tag_key]
        
        player.clan = tag
    
    ## Plugin Handles and Commands
    def handle_player_connect(self, player):
        if not self.inqueue(player):
            self.add(player)
    
    def handle_player_disconnect(self, player, reason):
        self.setPlaying(player)
        self.clAFKTag(player)
        self.rem(player)
    
    def handle_team_switch(self, player, old_team, new_team):
        if new_team == "spectator":
            if not self.inqueue(player):
                self.add(player)
            else:
               self.clRemPending(player)
        elif new_team != "spectator":
            self.setPlaying(player)
            self.clAFKTag(player)
            self.setRemPending(player)
    
    def handle_configstring(self, index, value):
        if not value:
            return
        
        elif 529 <= index < 529 + 64:
            player = self.player(index - 529)
            
            if self.inafk(player):
                self.setAFKTag(player)
                return minqlx.RET_STOP 
    
    def cmd_lq(self, player, msg, channel):
        self.clLists()
        self.RemPending()
        
        namesbytime = sorted(self._queue, key= lambda item: item["joinTime"])
        msg = "^7No one in queue."
        if self._queue:
            msg = "^1Queue^7 >> "
            for item in namesbytime:
                diff = datetime.datetime.now() - item["joinTime"]
                seconds = diff.days * 3600 * 24
                seconds = seconds + diff.seconds
                minutes = seconds // 60
                waiting_time = ""
                if minutes:
                    waiting_time = "^1{}m^7".format(minutes)
                else:
                    waiting_time = "^1{}s^7".format(seconds)
                
                if self.isRemPending(item["player"]):
                    msg += item["name"] + ": " + waiting_time + "^2*^7 "
                else:
                    msg += item["name"] + ": " + waiting_time + " "
        channel.reply(msg)
        
        if self._afk:
            namesbytime = sorted(self._afk, key = lambda item: item["joinTime"])
            msg = "^3Away^7 >> "
            for item in namesbytime:
                diff = datetime.datetime.now() - item["joinTime"]
                seconds = diff.days * 3600 * 24
                seconds = seconds + diff.seconds
                minutes = seconds // 60
                waiting_time = ""
                if minutes:
                    waiting_time = "^1{}m^7".format(minutes)
                else:
                    waiting_time = "^1{}s^7".format(seconds)
                
                msg += item["name"] + ": " + waiting_time + " "
            
            channel.reply(msg)
    
    def cmd_afk(self, player, msg, channel):
        if len(msg) > 1:
            if self.db.has_permission(player, self.get_cvar("qlx_queueSetAfkPermission", int)):
                guy = self.find_player(msg[1])[0]
                if self.setAFK(guy):
                    self.setAFKTag(guy)
                    player.tell("^7Status for {} has been set to ^3AFK^7.".format(guy.name))
                    return minqlx.RET_STOP_ALL
                else:
                    player.tell("Couldn't set status for {} to AFK.".format(guy.name))
                    return minqlx.RET_STOP_ALL
        if self.setAFK(player):
            self.setAFKTag(player)
            player.tell("^7Your status has been set to ^3AFK^7.")
        else:
            player.tell("^7Couldn't set your status to AFK.")

    def cmd_playing(self, player, msg, channel):
        if self.setPlaying(player):
            self.clAFKTag(player)
            player.tell("^7Your status has been set to ^2AVAILABLE^7.")
        else:
            player.tell("^7Couldn't set your status to AVAILABLE.")
