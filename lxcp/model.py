from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, event
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_jsonapi import permission_test, Permissions, relationship_descriptor, RelationshipActions
from flask import g

from collections import OrderedDict

from . import db
from .auth import StrukAuth

DB_Base = db.Model

class Serializable:
    def as_dict(self):
        return OrderedDict([(name, getattr(self, name)) for name, column in self.__mapper__.columns.items()])

    @permission_test(Permissions.VIEW)
    def can_view(self):
        # late import to avoid circular reference
        print('Checked can_view: {}'.format(self))
        from .lib import Lib
        sess = Lib.get_lib().session
        if sess.logged_in():
            user = sess.user()
            return self.is_visible_for(user)
        elif sess.node_authed():
            return True
        else:
            return False

    @permission_test(Permissions.EDIT)
    def can_edit(self):
        print('Checked can_edit: {}'.format(self))
        # late import to avoid circular reference
        from .lib import Lib
        sess = Lib.get_lib().session
        if sess.logged_in():
            user = sess.user()
            return self.is_writeable_for(user)
        elif sess.node_authed():
            return True
        else:
            return False

    @permission_test(Permissions.CREATE)
    def can_create(self):
        return self.can_edit()

    @permission_test(Permissions.DELETE)
    def can_delete(self):
        return self.can_edit()

class Group(DB_Base, Serializable):
    __tablename__ = 'group'
    id = Column('gid', Integer, primary_key=True)
    name = Column(String(50), unique=True)
    is_super = Column(Boolean)
    group_members = relationship("User", back_populates='group')
    group_shares = relationship("NFS", back_populates='group')

    def __init__(self, name=None, is_super=False):
        self.name = name
        self.is_super = is_super

    def __repr__(self):
        return '<Group {}>'.format(repr(self.name))

    def is_visible_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user in self.group_members:
            return True
        else:
            return False

    def is_writeable_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        else:
            return False

class User(DB_Base, Serializable):
    __tablename__ = 'user'
    id = Column('uid', Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.gid'))
    group = relationship("Group", back_populates='group_members')
    containers = relationship("Container", back_populates="user")
    username = Column(String)
    is_admin = Column(Boolean)

    def __init__(self, group=None, username=None, is_admin=None):
        self.group = group
        self.username = username
        self.is_admin = is_admin

    def __repr__(self):
        return '<User id={} username={}>'.format(self.id, self.username)

#    @relationship_descriptor(RelationshipActions.SET, 'group')
#    def group_setter(self, group_id):
#        self.group = Group.query.get(group_id)

    @property
    def is_super_admin(self):
        return self.is_admin and self.group.is_super

    def is_visible_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.group == self.group:
            return True

    def is_writeable_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.group == self.group and user.is_admin:
            return True
        else:
            return False

class Host(DB_Base, Serializable):
    __tablename__ = 'host'
    id = Column('hid', Integer, primary_key=True)
    slots = relationship("Slot", backref="host")
    containers = relationship("Container", back_populates="host")
    name = Column(String)
    ncpu = Column(Integer)
    nram = Column(Integer)
    nhdd = Column(Integer)

    def __init__(self, name=None, ncpu=None, nram=None, nhdd=None):
        self.name = name
        self.ncpu = ncpu
        self.nram = nram
        self.nhdd = nhdd

    def is_visible_for(self, user):
        if not user:
            return False
        return True

    def is_writeable_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        else:
            return False

class NFS(DB_Base, Serializable):
    __tablename__ = 'nfs'
    id = Column('nid', Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.gid'))
    group = relationship("Group", back_populates='group_shares')
    path = Column(String)
    mapping = Column(String)

    def __init__(self, group=None, path=None, mapping=None):
        self.group = group
        self.path = path
        self.mapping = mapping

    def is_visible_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.group == self.group:
            return True
        else:
            return False

    def is_writeable_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        else:
            return False

class Container(DB_Base, Serializable):
    __tablename__ = 'container'
    id = Column('cid', Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey('host.hid'))
    user_id = Column(Integer, ForeignKey('user.uid'))
    host = relationship("Host", back_populates="containers")
    user = relationship("User", back_populates="containers")
    slots = relationship("Slot", backref="container")
    name = Column(String)

    def __init__(self, host=None, user=None, name=None):
        self.host = host
        self.user = user
        self.name = name

    def is_visible_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.group == self.group:
            return True
        else:
            return False

    def is_writeable_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.is_admin and user.group == self.group:
            return True
        else:
            return False

class Slot(DB_Base, Serializable):
    __tablename__ = 'slot'
    id = Column('sid', Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey('container.cid'))
    host_id = Column(Integer, ForeignKey('host.hid'))
    hours = Column(Integer)
    ncpu = Column(Integer)
    nram = Column(Integer)

    def __init__(self, container, hours, ncpu, nram):
        self.container = container
        self.hours = hours
        self.ncpu = ncpu

    def is_visible_for(self, user):
        if not user:
            return False
        return True

    def is_writeable_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.is_admin and user.group == self.container.user.group:
            return True
        elif user == self.container.user:
            return True
        else:
            return False


