Stack Overflow Chat to IRC Server
---

this tool exposes an IRC server on port 6667 for localhost.
Connect to it using your favorite IRC client and you'll be
able to access all Stack Overflow channels.

![screenshot](http://m0g.net/stuff/sochat-sshot.png)

Disclaimer
---

This tool is really early stage, so it is still ugly and 
buggy, and may not work well. So be warned that you may 
get banned from SO, get pwned by the russian mafia or attacked
by a swarm of hungry trolls. I won't take any responsibility!

Build
---

to build the tool for development:

    % pip install zc.buildout
    % buildout

Use
---

once you've built it, it's easy:

    % bin/soirc_server

then open your favorite IRC client and connect to it:

    % irssi -c 127.0.0.1 -p 6667 -w PASSWORD -n LOGIN

where `PASSWORD` is your stackoverflow password and `LOGIN` your stackoverflow login
(which usually is your email). It's only supporting StackExchange openid service at
the time being, though it's easy to switch to google openid.

Implemented
---

 * login to SO using openid
 * join one channel
 * talk and lurk that channel
 * commands:
  * /whois
  * /whowas
  * /who
  * /names
  * /join
  * /list (which gives only the list of chans from chat.stackoverflow.com mainpage)
 * translates html from SO Chat server to markdown
 * breaks multiline messages in several messages

Known bugs (or bugs-alike)
---

 * no command line argument parsing (hint: add `docopt`), which could solve:
  * can only login through Stack Overflow OpenID (Google is supported as well but not available)
  * cannot change port
  * cannot change host
  * cannot change cookiejar
 * only one user can use the service
  * if two users connect → undefined/unknown behaviour (it may kill pandas)
 * there's a lot of exceptions in the log to be found
 * there's a lot of code that I'm not sure it's really useful
 * it's all in one file, it needs more modularity, dude!
 * only *one* chan can be joined at a time, that sucks, uh?
 * only *one* chat server can be connected to at a time
  * it could be possible to join channels on other servers as well... or have one server-proxy per SO chat server?
 * (with Ballmer's voice) bugs, bugs, bugs!

License
---

[![WTFPL](http://www.wtfpl.net/wp-content/uploads/2012/12/wtfpl-badge-4.png)](http://www.wtfpl.net)

    WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
    Version 2, December 2004 

    Copyright (C) 2004 Sam Hocevar <sam@hocevar.net> 

    Everyone is permitted to copy and distribute verbatim or modified 
    copies of this license document, and changing it is allowed as long 
    as the name is changed. 

    DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
    TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION 

    0. You just DO WHAT THE FUCK YOU WANT TO.

though I'm using a very permissive license, know that:

 1. if you do fork and make this work better and do not tell me, you're just a moron
 2. if you really like this software and want to thank me, well just fucking thank me!
 3. and if you fuckingly love that software, then please buy me a damn good beer!

