import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
activate_this = path + '/.venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

sys.path.insert(0, path)

from lxcp import app

application = app
