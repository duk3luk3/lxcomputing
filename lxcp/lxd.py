import pylxd

from .auth import StrukAuth

class LXClient:
    def __init__(self):
        self.client = pylxd.Client(
                endpoint='https://localhost:8443',
                cert=('/home/erlacher/.config/lxc/client.crt','/home/erlacher/.config/lxc/client.key'),
                verify=False
                )

    def cont_create(self, host, name):
        config = {'name': name, 'source': {'type': 'image', 'alias': 'xenial'}}
        container = self.client.containers.create(config, wait=False)
        return container

    def cont_get(self, host, name):
        container = self.client.containers.get(name)
        return container

    def cont_delete(self, host, name):
        container = self.client.containers.get(name)
        container.delete()

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
