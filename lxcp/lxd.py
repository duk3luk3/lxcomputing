import pylxd

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

