import pylxd
from pylxd.models.image import _image_create_from_config

from flask import current_app

from pathlib import Path

from .auth import StrukAuth
from .model import Host

import logging
logger = logging.getLogger(__name__)

class LXClient:
    def __init__(self):
        self.clients = {}
#        self.client = pylxd.Client(
#                endpoint='https://localhost:8443',
#                cert=('/home/erlacher/.config/lxc/client.crt','/home/erlacher/.config/lxc/client.key'),
#                verify=False
#                )

    def client_connect(self, hosts=None):
        if not hosts:
            hosts = Host.query.all()

        app = current_app
        key = app.config['LXKEY']
        cert = app.config['LXCERT']
        for host in hosts:
            if not host.name in self.clients:
                logger.debug('Connecting LXC Client to {}'.format(host.name))

                self.clients[host.name] = pylxd.Client(
                        endpoint='https://{}:8443'.format(host.name),
                        cert=(cert, key),
                        verify=False
                        )

    def client_trusted(self, host):
        logger.debug('Checking trust for {}'.format(host))
        return self.clients[host.name].trusted

    def client_trust(self, trust_pw, hosts=None):
        if not hosts:
            hosts = Host.query.all()
        self.client_connect(hosts)
        for host in hosts:
            if not self.client_trusted(hosts):
                self.clients[host.name].authenticate(trust_pw)

    def cont_create(self, host, container):
        name = container.name
        image = container.image
        if image:
            source = {'type': 'image', 'fingerprint': image}
        else:
            source = {'type': 'image', 'alias': 'xenial'}
        config = {'name': name, 'source': source}

        mappings = container.creator.group.group_shares

        if len(mappings) > 0:
            config['devices'] = {
                    mapping.mapping: {
                        'path': '/srv/' + mapping.mapping,
                        'source': '/compute/' + mapping.mapping,
                        'type': 'disk'
                    } for mapping in mappings
                }

        container = self.clients[host.name].containers.create(config, wait=True)
        return container

    def cont_get(self, host, name):
        container = self.clients[host.name].containers.get(name)
        return container

    def cont_delete(self, host, name):
        container = self.clients[host.name].containers.get(name)
        if container.status == 'Running':
            container.stop(wait=True)
        container.delete()

    def cont_provision(self, host, container):
        """Provision a container for use as a template

        * Starts the container if not running
        * Uploads and executes provisioning script
        * Converts container to template
        """
        cont = self.cont_get(host, container.name)
        if cont.status != 'Running':
            cont.start(wait=True)
        p = Path(__file__).parent / 'files' / 'provision.sh'
        with p.open() as f:
            script = f.read()
        cont.files.put('/root/provision.sh', script)
        cmd = ['chmod', '+x', '/root/provision.sh']
        res = cont.execute(cmd)
        print(res)
        cmd = ['/bin/bash', '-x', '-c', '/root/provision.sh']
        res = cont.execute(cmd)
        print(res)
        cmd = ['poweroff']
        res = cont.execute(cmd)
        print(res)
        try:
            cont.stop(wait=True)
        except:
            pass
        #TODO: Use container.publish (but then can't pass alias)
        image_config = {
                'aliases': [
                    {
                        'name': 'lxtemplate-' + container.name,
                        'description': 'New LXC Template'
                    }
                    ],
                'source': {
                    'type': 'container',
                    'name': container.name
                    }
                }
        _image_create_from_config(self.clients[host.name], image_config, wait=True)


    def cont_init(self, host, container):
        """Initialize a new container"""
        pass

    def cont_adduser(self, host, container, user):
        cnt = self.cont_get(host, container.name)
        if cnt.status != 'Running':
            cnt.start(wait=True)
        suser = StrukAuth.get_userdata(user.username)
        add_cmd = ['adduser',
                '--uid', str(suser['uidNumber']),
                '--disabled-password',
                '--gecos', suser['givenName'] + ' ' + suser['sn'],
                suser['uid']
                ]
        res = cnt.execute(add_cmd)
        print('add_cmd_res', res)
        group_cmd = ['adduser', suser['uid'], 'root']
        res = cnd.execute(group_cmd)
        print('group_cmd_res', res)
        pwd = suser['password']
        if pwd.lower().startswith('{crypt}'):
            pwd_hash = pwd[len('{crypt}'):]
            pwd_cmd = ['usermod',
                    '-p', pwd_hash,
                    suser['uid']
                    ]
            res = cnt.execute(pwd_cmd)
            print('res', res)
        sshkey = user.sshkey
        if sshkey:
            ssh_cmd = ['sudo', '-u', suser['uid'], 'bash', '-x', '-c', 'cd /home/{}; umask 077; test -d .ssh || mkdir .ssh ; echo -e {} >> .ssh/authorized_keys'.format(suser['uid'], sshkey.replace('\n', '\\n'))]
            res = cnt.execute(ssh_cmd)
            print('cmd', ssh_cmd, 'res', res)

    def cont_deluser(self, host, container, user):
        cnt = self.cont_get(host, container.name)
        uname = user.username
        del_cmd = ['deluser', uname]
        res = cnt.execute(del_cmd)
        print('res', res)

    def images(self, host):
        if not host:
            host = Host.query.first()
        if not host:
            return []
        return self.clients[host.name].images.all()

