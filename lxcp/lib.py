import glob
import os
import sys

from flask import g, session
from sqlalchemy import event

from . import db, redis_store
from .model import *
from .auth import StrukAuth

@event.listens_for(Container, 'after_insert')
def container_insert(mapper, connection, container):
    redis_store.rpush('events.container.insert', container.id)

    print(container)

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
    HELLO = 'hello'
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
            db = Lib.get_db()
            lib = g._lib = Lib(sess)
        return lib

    def __init__(self, session):
        self.session = session

    def _ok(self, content):
        session_data = {
            'logged_in': self.session.logged_in(),
            'name': self.session.username(),
            'user': self.session.user()
            }
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

    def login(self, username, password):
        return self.session.password_auth(username, password)

    def index(self):
        if self.session.logged_in():
            return self._ok(
                    {
                        'links': [
                            ('setup', '/setup'),
                            ('data', '/data'),
                            ('users', '/users'),
                            ('ressources', '/res'),
                            ('containers', '/containers'),
                        ],
                    },
                )
        else:
            return self._ok(
                    self.HELLO,
                )

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


class Session:
    def __init__(self, session):
        self.session = session

    def logged_in(self):
        return 'username' in self.session

    def username(self):
        return self.session.get('username', None)

    def user(self):
        user = self.session.get('user', None)
        if user:
            user_obj = User.query.filter(User.id == user).one()
            return user_obj
        return user

    def password_auth(self, username, password):
        if StrukAuth.test(username, password):
            print('login success ({})'.format(username))
            udata = StrukAuth.get_userdata(username)
            dbu = User.query.filter(User.username == udata['uid']).one_or_none()
            self.set_login(username, dbu)
            return True
        else:
            print('login fail ({})'.format(username))
            self.fail_login()
            return False

    def set_login(self, username, user):
        self.session['username'] = username
        if user:
            self.session['user'] = user.id
        self.session['failed'] = False

    def fail_login(self):
        self.session['failed'] = True

    def get_fail(self):
        return self.session.get('failed', False)

    def clear_login(self):
        self.session.pop('username')

