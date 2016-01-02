# minqlx-plugins
This is a collection of plugins that I wrote for Mino's Quake Live Server Mod [minqlx](https://github.com/MinoMino/minqlx). 

## queue.py
This is a queue plugin. Some parts of it were inspired by the original queueinfo plugin which was
written by [walkerX](https://github.com/WalkerY/minqlbot-plugins/tree/queueinfo/plugins) for the old minqlbot.

### Info
The plugin basically shows for how long people have been waiting in specator
mode. If a player joins a team, the name is kept for three minutes (so admins
can track players that dont respect the queue) in the list but now displayed
with an asterisk to show that the player has left the queue and will soon be
removed.

The plugin also features an AFK list, to which players can 
subscribe/unsubscribe to.

## pummel.py
This is a fun plugin.

### Info
It displays "Killer x:y Victim" message when Victim gets killed with gauntlet
and stores the information in REDIS DB

Players can display their "pummels" via !pummel - this works only for victims
that are on the server at the same time, otherwise we could just spit out
steamIDs.
