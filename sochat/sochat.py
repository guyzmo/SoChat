import sys

from zope.interface import implements

from twisted.words import iwords, ewords

from twisted.words.protocols.irc import IRC
from twisted.internet import defer, protocol, task
from twisted.cred import checkers, portal, credentials, error as ecred
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.python import log, failure, reflect
from twisted.words.service import IRCUser, IRCFactory, User, Group
from twisted.words.protocols import irc

from time import ctime

from stackoverflow.auth_stackoverflow import StackOverflow_SOAuth
from stackoverflow.utils import html2md, authenticate

class IExternalChecker():
    def checkPassword(self, c):
        raise NotImplementedError

    def getNickname(self):
        raise NotImplementedError

class StackOverflowAdapter(IExternalChecker):
    def __init__(self, target, cookiejar):
        self.so = StackOverflow_SOAuth(None, None, target, cookiejar)

    def __enter__(self):
        self.so = self.so.__enter__()
        return self

    def __exit__(self, *args):
        self.so.__exit__(*args)

    def checkPassword(self, c):
        self.so.username = c.username
        self.so.password = c.password
        try:
            self.so.authenticate()
        except:
            return False
        return self.so.is_authenticated()

    def getMyUserData(self):
        return self.so.get_my_info()

    def channels(self):
        for key, room in self.so.list_all_rooms().iteritems():
            yield SoGroup(self, unicode(key), ['']*int(room['nb_users']), {'topic': room['topic'], 'topic_author':''})

    def lookupgroup(self, name):
        room = self.so.get_room_info(int(name))
        if room:
            return room
        return None


    def lookupuser(self, name):
        pass
        # if name in self.so.list_all_rooms():
        #     return defer.succeed(name)
        # return defer.fail(failure.Failure(ewords.NoSuchGroup(name)))


    def post(self, room, msg):
        self.so.send_to_chat(int(room), msg)

class ExternalCredentialsChecker:
    """
    An extremely simple credentials checker.

    This is only of use in one-off test programs or examples which don't
    want to focus too much on how credentials are verified.

    You really don't want to use this for anything else.  It is, at best, a
    toy.  If you need a simple credentials checker for a real application,
    see L{FilePasswordDB}.
    """

    implements(checkers.ICredentialsChecker)

    credentialInterfaces = (credentials.IUsernamePassword,)

    def __init__(self, ext):
        self.ext = ext


    def _cbPasswordMatch(self, matched, username):
       if matched:
           return self.ext.getMyUserData().values() + [username,]
       log.msg("User failed to log: {}".format(username))
       return failure.Failure(error.UnauthorizedLogin())

    def requestAvatarId(self, c):
        log.msg("requestAvatarId {}".format(c.username))
        return defer.maybeDeferred(self.ext.checkPassword, c).addCallback(self._cbPasswordMatch, c.username)

class SoChatIRCUser(IRCUser):
    _motdMessages = [
        (irc.RPL_MOTDSTART, ":- %(serviceName)s Message of the Day - "),
        (irc.RPL_MOTD, "                        ---                     "),
        (irc.RPL_MOTD, "Welcome on the Stack Overflow Chat to IRC Server"),
        (irc.RPL_MOTD, "                        ---                     "),
        (irc.RPL_MOTD, "                                                "),
        (irc.RPL_MOTD, "Only *you* can login here, if it's not you, then"),
        (irc.RPL_MOTD, "get away, you're not welcome here.              "),
        (irc.RPL_MOTD, "                                                "),
        (irc.RPL_MOTD, "Have fun!                                       "),
        (irc.RPL_ENDOFMOTD, ":End of /MOTD command.")
    ]

    def connectionMade(self):
        self.irc_PRIVMSG = self.irc_NICKSERV_PRIVMSG
        self.realm = self.factory.realm
        self.hostname = self.realm.name
        print "CONNECTION MADE", self
        self.realm.clients.append(self)

    def irc_WHOWAS(self, prefix, args):
        print "irc_WHOWAS", prefix, args, self.realm.users
        self.sendMessage(irc.RPL_WHOISUSER, args[0], "USERNAME", self.realm.name, '*', ':' + "REALNAME")
        self.sendMessage(irc.RPL_WHOISSERVER, args[0], 'server', ':' + self.realm.name)

    def irc_WHOIS(self, prefix, params):
        """Whois query

        Parameters: [ <target> ] <mask> *( "," <mask> )
        """
        def cbUser(user):
            self.whois(
                self.name,
                user.name, user.name, self.realm.name,
                user.name, self.realm.name, 'SoChat IRC Gateway', False,
                int(time() - user.lastMessage), user.signOn,
                ['#' + group.name for group in user.itergroups()])

        def ebUser(err):
            err.trap(ewords.NoSuchUser)
            self.sendMessage(
                irc.ERR_NOSUCHNICK,
                user,
                params[0],
                ":No such nick/channel")

        try:
            user = params[0].decode(self.encoding)
        except UnicodeDecodeError:
            self.sendMessage(
                irc.ERR_NOSUCHNICK,
                user,
                params[0],
                ":No such nick/channel")
            return

        self.realm.lookupUser(user).addCallbacks(cbUser, ebUser)


class SoChatIRCFactory(IRCFactory):
    protocol = SoChatIRCUser

import time

class SoUser(User):
    def __init__(self, name, user=None, real=None, host=None):
        print "SoUser", name, user, real, host
        User.__init__(self, name)
        self.userLeft = 0
        self.userJoined = 0
        self.signOn = 0
        self.username = user
        self.realname = real
        self.hostname = host

class SoGroup(Group):
    def __init__(self, realm, name, users = {}, meta={"topic":"", "topic_author":""}):
        self.realm = realm
        self.so = realm.so

        self.name = name
        self.users = users
        self.meta = meta

        self.first_call = True
        def cb(msg):
            for c in self.realm.clients:
                # used to show nicknames when loading previous discussions,
                # looks like xchat does not like that, but irssi has no problem
                # with it.
                if not self.first_call and c.name == msg['user_name']:
                    continue
                # we get multiline content, so first, let's split it
                for sub_msg in html2md(msg['content']).splitlines():
                    # weed out empty lines
                    if len(sub_msg.strip()) > 0:
                        # send the message to the user by building the names
                        c.privmsg("{}!{}@{}".format(msg['user_name'].lower().replace(' ','-'), msg['user_id'], self.name),
                                '#{}'.format(self.name), sub_msg)
        refresh = self.so.so.connect_to_chat(int(self.name), cb)
        def cb_refresh():
            return refresh()
        self.watch = task.LoopingCall(cb_refresh)
        self.watch.start(2)

    def stop(self):
        self.watch.stop()

    def receive(self, sender, recipient, message):
        assert recipient is self
        self.so.post(recipient.name, message['text'])

class SoChatRealm(object):
    implements(portal.IRealm, iwords.IChatService)

    _encoding = 'utf-8'

    def __init__(self, name, so):
        self.name = name
        self.so = so
        self.groups = {}
        self.users = {}
        self.clients = []

    def userFactory(self, name, i=None, f=None):
        print "USER FACTORY", name, i ,f
        if i and f:
            return SoUser(name, f.split('@')[0], i, f.split('@')[-1])
        return SoUser(name)


    def groupFactory(self, name):
        print "GROUP FACTORY", name
        group = self.so.lookupgroup(name)
        if group:
            try:
                print group['users']
                group = SoGroup(self, unicode(name),
                            dict([(u[0], SoUser(*u)) for u in group['users']]),
                            {'topic': group['topic'],
                            'topic_author':''})
                self.groups[name] = group
                return group
            finally:
                group.first_call = False
        else:
            return None


    def logoutFactory(self, avatar, facet):
        print "LOGOUT FACTORY", avatar, facet
        def logout():
            # XXX Deferred support here
            getattr(facet, 'logout', lambda: None)()
            avatar.realm = avatar.mind = None
        return logout


    def requestAvatar(self, avatarId, mind, *interfaces):
        print "REQ AVATAR", avatarId, mind, interfaces
        if isinstance(avatarId, str):
            avatarId = avatarId.decode(self._encoding)
        if isinstance(avatarId, list):
            avatarName = avatarId[0]
            avatarUser = avatarId[1]
            avatarHost = avatarId[2]
        def gotAvatar(avatar):
            if avatar.realm is not None:
                raise ewords.AlreadyLoggedIn()
            for iface in interfaces:
                facet = iface(avatar, None)
                if facet is not None:
                    avatar.loggedIn(self, mind)
                    mind.name = avatarName
                    mind.realm = self
                    mind.avatar = avatar
                    return iface, facet, self.logoutFactory(avatar, facet)
            raise NotImplementedError(self, interfaces)

        return self.createUser(*avatarId).addCallback(gotAvatar)


    # IChatService, mostly.
    createGroupOnRequest = False
    createUserOnRequest = True


    def getGroup(self, name):
        print "GETGROUP", name
        assert isinstance(name, unicode)
        def ebGroup(err):
            err.trap(ewords.NoSuchGroup)
            return self.createGroup(name)
        return self.lookupGroup(name).addErrback(ebGroup)

    def getUser(self, name):
        print "GETUSER", name
        assert isinstance(name, unicode)
        if self.createUserOnRequest:
            def ebUser(err):
                err.trap(ewords.DuplicateUser)
                return self.lookupUser(name)
            return self.createUser(name).addErrback(ebUser)
        return self.lookupUser(name)


    def createUser(self, name, i=None, f=None):
        print "CREATEUSER", name
        assert isinstance(name, unicode)
        def cbLookup(user):
            return failure.Failure(ewords.DuplicateUser(name))
        def ebLookup(err):
            err.trap(ewords.NoSuchUser)
            return self.userFactory(name, i, f)

        name = name.lower()
        d = self.lookupUser(name)
        d.addCallbacks(cbLookup, ebLookup)
        d.addCallback(self.addUser)
        return d


    def createGroup(self, name):
        print "CREATEGROUP", name
        assert isinstance(name, unicode)
        def cbLookup(group):
            return failure.Failure(ewords.DuplicateGroup(name))
        def ebLookup(err):
            err.trap(ewords.NoSuchGroup)
            return self.groupFactory(name)

        name = name.lower()
        d = self.lookupGroup(name)
        d.addCallbacks(cbLookup, ebLookup)
        d.addCallback(self.addGroup)
        return d


    def itergroups(self):
        print "ITERGROUPS"
        return defer.succeed(self.so.channels())

    def addUser(self, user):
        print "ADDUSER", user.name
        return defer.succeed(user)

    def addGroup(self, group):
        print "ADDGROUP", group.name
        self.groups[group.name] = group
        return defer.succeed(group)

    def lookupUser(self, name):
        print "LOOKUPUSER", name
        assert isinstance(name, unicode)

        users = {}
        for g in self.groups.values():
            users.update(g.users)

        if name in users:
            return defer.succeed(users[name])

        if self.so.lookupuser(name):
            return defer.succeed(SoUser(name))
        else:
            return defer.fail(failure.Failure(ewords.NoSuchUser(name)))

    def lookupGroup(self, name):
        print "LOOKUPGROUP", name
        assert isinstance(name, unicode)

        if name in self.groups:
            return defer.succeed(self.groups[name])

        return defer.fail(failure.Failure(ewords.NoSuchGroup(name)))


def run():
    log.startLogging(sys.stdout)


    with StackOverflowAdapter("stackoverflow.com", "~/.so.cookie.jar") as so:
        # Initialize the Cred authentication system used by the IRC server.
        realm = SoChatRealm('chat.stackoverflow.com', so)

        user_db = ExternalCredentialsChecker(so)
        p = portal.Portal(realm, [user_db])

        # IRC server factory.
        ircfactory = SoChatIRCFactory(realm, p)

        # Connect a server to the TCP port 6667 endpoint and start listening.
        endpoint = TCP4ServerEndpoint(reactor, 6667)
        endpoint.listen(ircfactory)

        reactor.run()

if __name__ == '__main__':
    run()
