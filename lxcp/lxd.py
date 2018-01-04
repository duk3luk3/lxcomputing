import pylxd

from pathlib import Path

from .auth import StrukAuth

class LXClient:
    def __init__(self):
        self.client = pylxd.Client(
                endpoint='https://localhost:8443',
                cert=('/home/erlacher/.config/lxc/client.crt','/home/erlacher/.config/lxc/client.key'),
                verify=False
                )

    def cont_create(self, host, name, image):
        if image:
            source = {'type': 'image', 'fingerprint': image}
        else:
            source = {'type': 'image', 'alias': 'xenial'}
        config = {'name': name, 'source': source}
        container = self.client.containers.create(config, wait=False)
        return container

    def cont_get(self, host, name):
        container = self.client.containers.get(name)
        return container

    def cont_delete(self, host, name):
        container = self.client.containers.get(name)
        container.delete()

    def cont_provision(self, host, container):
        """Provision a container for use as a template"""
        cont = self.cont_get(host, container.name)
        if cont.status != 'RUNNING':
            cont.start()
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


    def cont_init(self, host, container):
        """Initialize a new container"""
        pass

    def cont_adduser(self, host, container, user):
        cnt = self.cont_get(host, container.name)
        suser = StrukAuth.get_userdata(user.username)
        add_cmd = ['adduser',
                '--uid', str(suser['uidNumber']),
                '--disabled-password',
                '--gecos', suser['givenName'] + ' ' + suser['sn'],
                suser['uid']
                ]
#        rout, rerr = cnt.execute(add_cmd)
#        print('rout:', rout)
#        print('rerr:', rerr)
        res = cnt.execute(add_cmd)
        print('res', res)
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
            ssh_cmd = ['sudo', '-u', 'erlacher', 'bash', '-x', '-c', 'cd /home/{}; umask 077; test -d .ssh || mkdir .ssh ; echo {} >> .ssh/authorized_keys'.format(suser['uid'], sshkey)]
            res = cnt.execute(ssh_cmd)
            print('cmd', ssh_cmd, 'res', res)

    def cont_deluser(self, host, container, user):
        cnt = self.cont_get(host, container.name)
        uname = user.username
        del_cmd = ['deluser', uname]
        res = cnt.execute(del_cmd)
        print('res', res)

    def images(self, host):
        return self.client.images.all()

