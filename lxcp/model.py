from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, event, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_jsonapi import permission_test, Permissions, relationship_descriptor, RelationshipActions
from flask import g, current_app

from collections import OrderedDict

from . import db
from .auth import StrukAuth

DB_Base = db.Model

class Serializable:
    def as_dict(self):
        return OrderedDict([(name, getattr(self, name)) for name, column in self.__mapper__.columns.items()])

    def save(self):
        if self.id == None:
            db.session.add(self)
        return db.session.commit()

    @permission_test(Permissions.VIEW)
    def can_view(self):
        # late import to avoid circular reference
        print('Checked can_view: {}'.format(self))
        from .lib import Lib
        sess = Lib.get_lib().session
        if sess.logged_in():
            user = sess.user()
            return self.is_visible_for(user)
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

ContainerUsers = Table('container_user', DB_Base.metadata,
        Column('container_id', Integer, ForeignKey('container.cid')),
        Column('user_id', Integer, ForeignKey('user.uid'))
        )

class User(DB_Base, Serializable):
    __tablename__ = 'user'
    id = Column('uid', Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.gid'))
    group = relationship("Group", back_populates='group_members')
    containers = relationship("Container",
            secondary=ContainerUsers,
            back_populates="users")
    created_containers = relationship("Container", back_populates='creator')
    username = Column(String)
    is_admin = Column(Boolean)
    sshkey = Column(String)

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

    def calc_utilisation(self):
        pending_slots = [slot for slot in self.slots if slot.hours > slot.hours_used]

        cpu = sum(slot.ncpu for slot in pending_slots)
        ram = sum(slot.nram for slot in pending_slots)

        utilisation = max(cpu / self.ncpu, ram / self.nram)

        return {'cpu_demand': cpu, 'ram_demand': ram, 'utilisation': utilisation}


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
    creator_id = Column(Integer, ForeignKey('user.uid'))
    host = relationship("Host", back_populates="containers")
    creator = relationship("User", back_populates="created_containers")
    slots = relationship("Slot", backref="container")
    users = relationship("User",
            secondary=ContainerUsers,
            back_populates="containers")
    name = Column(String)
    image = Column(String)

    def __init__(self, host=None, owner=None, name=None):
        self.host = host
        self.owner = owner
        self.name = name

    def __repr__(self):
        return '<Container {}>'.format(repr(self.name))

    def is_visible_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.group == self.creator.group:
            return True
        else:
            return False

    def is_writeable_for(self, user):
        if not user:
            return False
        if user.is_super_admin:
            return True
        elif user.is_admin and user == self.creator:
            return True
        else:
            return False

    def lxc(self):
        from .lib import Lib
        lib = Lib.get_lib()
        return lib.lxclient.cont_get(self.host, self.name)

    @hybrid_property
    def status(self):
        if not hasattr(self, '_status'):
            self._status = self.lxc().status
        return self._status

    @status.setter
    def status(self, status):
        container = self.lxc()
        actions = {
                'stop': container.stop,
                'start': container.start,
                'restart': container.restart,
                'freeze': container.freeze,
                'unfreeze': container.unfreeze
        }
        action = actions.get(status)
        if action:
            action()
            if hasattr(self, '_status'):
                delattr(self, '_status')
        else:
            raise ValueError('Available status values: {}'.format(', '.join(actions.keys())))

    def actions(self):
        status = self.status
        actions = {
                'Running': ['stop', 'freeze', 'restart'],
                'Stopped': ['start'],
                'Frozen': ['unfreeze', 'stop']
                }
        return actions[status]

    def schedule(self):
        """Start container if not started
        """
        if not self.status == 'Running':
            self.status = 'start'

    def unschedule(self):
        """Stop container is running
        """
        if self.status == 'Running':
            self.status = 'stop'


class Slot(DB_Base, Serializable):
    __tablename__ = 'slot'
    id = Column('sid', Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey('container.cid'))
    host_id = Column(Integer, ForeignKey('host.hid'))
    hours = Column(Integer)
    hours_used = Column(Integer)
    ncpu = Column(Integer)
    nram = Column(Integer)

    def __init__(self, container=None, hours=None, hours_used=None, ncpu=None, nram=None):
        self.container = container
        self.hours = hours or 0
        self.hours_used = hours_used or 0
        self.ncpu = ncpu or 0
        self.nram = nram or 0

    @hybrid_property
    def instance(self):
        return None

    @instance.setter
    def instance(self, value):
        app = current_app
        instances = app.config['LXCP_INSTANCES']
        inst = None
        for instance in instances:
            if instance['name'] == value:
                inst = instance
                break
        if inst:
            self.ncpu = inst['cpu']
            self.nram = inst['ram']
        else:
            raise KeyError('Cannot find instance {}'.format(value))

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

    def __repr__(self):
        return '<Slot id={}: container={}, ncpu={}, nram={}, hours={}, hours_used={}>'.format(
                repr(self.id), repr(self.container.name) if self.container else 'None', repr(self.ncpu), repr(self.nram), repr(self.hours), repr(self.hours_used))


