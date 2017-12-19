#! python

raise KeyError()

from flask import Flask, g, jsonify, abort, redirect, url_for, make_response, render_template, request, session, send_from_directory
from flask.json import JSONEncoder
from flask_sqlalchemy import SQLAlchemy

from lib import Lib, Data, User, Session, StrukAuth
from .model import *

import os

app = Flask(__name__)
DBFILE = os.environ.get('DBFILE', '/srv/lxcompute/lxcompute.sqlite3')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DBFILE
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(db)

class BetterEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, 'as_dict'):
            return o.as_dict()
        else:
            return JSONEncoder.default(self, o)

app.json_encoder = BetterEncoder

def lib_render(lib_response):
    return make_response(
        jsonify(lib_response),
        '{status} {reason}'.format(**lib_response)
        )

@app.route('/static/<fname>')
def static_file(fname):
    return send_from_directory('static', fname)

@app.route('/api/v1/hello')
def api_v1_hello():
    lib = Lib.get_lib()
    response = lib.hello()
    return lib_render(response)

@app.route('/api/v1/data')
def api_v1_data():
    lib = Lib.get_lib()
    response = lib.data()
    return lib_render(response)

@app.route('/api/v1/data/<typ>')
def api_v1_data_typ(typ):
    lib = Lib.get_lib()
    cls = Lib.CLASSES.get(typ)
    if not cls:
        return lib._fail()
    if request.method == 'GET':
        _id = request.args.get('id', type=int)
        if _id:
            return lib_render(lib.data_get(cls, _id))
        else:
            return lib_render(lib.data({typ: cls}))
    elif request.method == 'POST':
        pass

@app.route('/')
def index():
    lib = Lib.get_lib()

    response = lib.index()
    print(response)
    return render_template('index.html', **response)

@app.route('/login', methods=['POST'])
def login():
    lib = Lib.get_lib()

    username = request.form['username']
    password = request.form['password']

    lib.login(username, password)
    return redirect('/')

@app.route('/logout')
def logout():
    user_session = Session(session)
    user_session.clear_login()

    return redirect('/')

@app.route('/setup')
def setup():
    db = get_db()

    return render_template('setup.html', populated=db.is_db_populated())

@app.route('/setup/db_populate', methods=['POST'])
def db_populate():
    print('populate')
    db = get_db()
    print(db)
    user_session = Session(session)

    populated = db.db_populate(user_session)

    if not populated:
        return 'Error'
    else:
        return redirect('/setup')

@app.route('/data/')
def show_data():
    lib = Lib.get_lib()
    response = lib.data()
    return render_template('index.html', **response)

@app.route('/users/')
def if_users():
    lib = Lib.get_lib()
    response = lib.data(classes=({'groups':Group, 'users':User}))
    return render_template('users.html', **response)

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == '__main__':
    app.run(debug=True)
