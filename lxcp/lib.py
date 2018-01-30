import glob
import os
import sys

from flask import g, session, current_app
from sqlalchemy import event

from . import db, api
from .model import *
from .auth import StrukAuth
from . import lxd

@event.listens_for(Container, 'after_insert')
def container_insert(mapper, connection, container):
    host = container.host
    client = lxd.LXClient()
    client.cont_create(host, container)

@event.listens_for(Container, 'after_delete')
def container_delete(mapper, connection, container):
    host = container.host
    client = lxd.LXClient()
    client.cont_delete(host, container.name)

@event.listens_for(Container.users, 'append')
def container_user_append(container, user, initiator):
    client = lxd.LXClient()
    host = container.host
    client.cont_adduser(host, container, user)

@event.listens_for(Container.users, 'remove')
def container_user_append(container, user, initiator):
    client = lxd.LXClient()
    host = container.host
    client.cont_deluser(host, container, user)

class Data:
    DBFILE = '/srv/lxcompute/lxcompute.sqlite3'
    SCHEMADIR = 'db_schema'

    def __init__(self, db_session):

#        self.db_session = scoped_session(sessionmaker(autocommit=False,
#                                                 autoflush=False,
#                                                 bind=self.engine))

        self.db_session = db_session

#    def __del__(self):
#        self.db_session.remove()


    def is_db_populated(self):
        return User.query.first() is not None

    def db_populate(self, user_session):
        if User.query.first() is None:
            username = user_session.username()
            userdata = StrukAuth.get_userdata(username)

            if userdata is not None and userdata['isRootUser']:
                group = Group(name=userdata['org'], is_super=True)
                user = User(
                    group=group,
                    username=userdata['uid'],
                    is_admin=True
                )
                self.db_session.add(group)
                self.db_session.add(user)
                self.db_session.commit()

                user_session.session['user'] = user.id

                return True
        else:
            print('User not empty', file=sys.stderr)
            return False

class Lib:
    HELLO = 'Welcome to LXC Compute, please log in using your RBG username and password'
    CLASSES = dict(
            groups=Group,
            users=User,
            hosts=Host,
            nfs=NFS,
            containers=Container,
            slots=Slot
    )

    @staticmethod
    def get_db():
        data = getattr(g, '_data', None)
        if data is None:
            print(db)
            print(db.session)
            data = g._data = Data(db.session)
        return data

    @staticmethod
    def get_lib():
        lib = getattr(g, '_lib', None)
        if lib is None:
            sess = Session(session)
            lib = g._lib = Lib(sess)
        return lib

    def __init__(self, session):
        self.session = session
        self.lxclient = lxd.LXClient()

    def _ok(self, content={}):
        session_data = {
            'logged_in': self.session.logged_in(),
            'login_failed': self.session.get_fail(),
            'name': self.session.username(),
            'real_name': self.session.real_username(),
            'user': self.session.user(),
            'real_user': self.session.real_user()
            }
        if self.session.logged_in():
            content.update({
                        'links': [
                            ('users', 'if_users'),
                            ('ressources', 'if_res'),
                            ('containers', 'if_containers'),
                            ('scheduling', 'if_schedule'),
                        ],
                        })
            if self.session.user().is_super_admin:
                content['links'].append(('setup', 'setup'))
                content['links'].append(('data', 'show_data'))
        else:
            content = self.HELLO
        return {
            'status': 200,
            'reason': 'OK',
            'content': content,
            'session_data': session_data
        }

    def _fail(self, content=None, status=400, reason='Usage error'):
        return {
                'status': status,
                'reason': reason,
                'content': content
            }

    def _filter(self, objects, for_write=False):
        if for_write:
            return [o for o in objects if o.is_writeable_for(self.session.user())]
        else:
            return [o for o in objects if o.is_visible_for(self.session.user())]

    def hello(self):
        return self._ok(self.HELLO)

    @staticmethod
    def return_user(user):
        return self._ok(repr(user))

    def login(self, username, password, impersonate):
        if impersonate:
            return self.session.impersonate(username)
        else:
            return self.session.password_auth(username, password)

    def index(self):
        return self._ok()

    def data(self, classes=None):
#        if self.session.logged_in():
        if True:

            if not classes:
                classes = self.CLASSES

            data = {k: self._filter(cls.query.all()) for (k, cls) in classes.items()}

            return self._ok(
                    data
                    )
        else:
            pass

    def data_get(self, cls, id_):
        return self._ok(cls.query.get(id_))

    def container_provision(self, container_id):

        client = self.lxclient
        container = Container.query.get(container_id)
        client.cont_provision('', container)


class Session:
    def __init__(self, session):
        self.session = session

    def logged_in(self):
        return 'real_username' in self.session

    def username(self):
        return self.session.get('impersonated_username', self.real_username())

    def real_username(self):
        return self.session.get('real_username', None)

    def real_user(self):
        user = self.session.get('real_user', None)
        if user:
            user_obj = User.query.filter(User.id == user).one()
            return user_obj
        return user

    def user(self):
        user = self.session.get('impersonated_user')
        if user:
            user_obj = User.query.filter(User.id == user).one()
            return user_obj
        else:
            return self.real_user()

    def password_auth(self, username, password):
        if StrukAuth.test(username, password):
            print('login success ({})'.format(username))
            udata = StrukAuth.get_userdata(username)
            dbu = self._update_user(username, udata)
            self.set_login(username, dbu)
            return True
        else:
            print('login fail ({})'.format(username))
            self.fail_login()
            return False

    def impersonate(self, username):
        real_user = self.real_user()
        if real_user:
            if real_user.is_admin:
                strukuser = StrukAuth.get_userdata(username)
                if strukuser['org'] == real_user.group.name or real_user.is_super_admin:
                    db_user = self._update_user(username, strukuser)
                    self.set_impersonated(username, db_user)
                    return True
            else:
                self.fail_login('Only admins can impersonate')
        return False


    def set_login(self, username, user):
        self.session['real_username'] = username
        if user:
            self.session['real_user'] = user.id
        self.session['failed'] = False

    def set_impersonated(self, username, user):
        self.session['impersonated_username'] = username
        if user:
            self.session['impersonated_user'] = user.id

    def fail_login(self, val=True):
        self.session['failed'] = val

    def get_fail(self):
        return self.session.get('failed', False)

    def clear_login(self):
        self.clear_impersonation()
        self.session.pop('real_username')
        self.session.pop('real_user')

    def clear_impersonation(self):
        if 'impersonated_username' in self.session:
            self.session.pop('impersonated_username')
            self.session.pop('impersonated_user')

    def _update_user(self, username, strukdata):
        """Synchronize user/org data from StrukturDB

        We synchronize this data every time a user logs in,
        and can operate without a strukturdb connection as long as a user
        has a logged in session.

        We don't overwrite the is_admin property since that can be changed.
        """
        db_user = User.query.filter(User.username == strukdata['uid']).one_or_none()
        if not db_user:
            db_user = User(group=None, username=username, is_admin=strukdata['isAdmin'])

        struk_group = strukdata['org']
        db_group = Group.query.filter(Group.name == struk_group).one_or_none()

        if not db_group:
            make_super = User.query.first() is None
            db_group = Group(struk_group, make_super)
            db_group.save()

        if db_user.group != db_group:
            db_user.group = db_group

        if strukdata['sshKey']:
            db_user.sshkey = '\n'.join(strukdata['sshKey'])
        db_user.save()
        return db_user


