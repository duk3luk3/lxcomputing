from struk.procedures import pwtest
from struk.registers import User, Group

class StrukAuth:

    @staticmethod
    def test(username, password):
        try:
            if not username.startswith('user:'):
                username = 'user:fmi:' + username
                print('Changed username to', username)
            return pwtest(user=username, password=password).return_dict['correct_auth']
        except:
            return False

    @staticmethod
    def get_userdata(username):
        if not username.startswith('user:'):
            username = 'user:fmi:' + username
        user = User.get(username)
        if user is not None:
            return {
                'uid': user.uid,
                'org': str(user.org.UQN),
                'uidNumber': user.uidNumber,
                'isRootUser': Group['fmi', 'rbg'] in user.backreferences['group.member'],
                'password': user.password,
                'sn': user.sn,
                'givenName': user.givenName
            }
        else:
            return None

    @staticmethod
    def get_username(uidNumber):
        user = list(User.select('(&(realm=fmi)(uidNumber={}))'.format(uidNumber)))
        if user:
            return user[0].uid
        else:
            return None

