#! python

from flask import Flask, g, jsonify, abort, redirect, url_for, make_response, render_template, request, session, send_from_directory
from flask.json import JSONEncoder
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_jsonapi import FlaskJSONAPI
from flask_redis import FlaskRedis
import os

app = Flask(__name__)
DBFILE = os.environ.get('DBFILE', '/srv/lxcompute/lxcompute.sqlite3')
REDIS_URL = "redis://:@localhost:6379/0"
app.config['REDIS_URL'] = REDIS_URL
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DBFILE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DBFILE
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SERVER_NAME'] = os.environ.get('FLASK_SERVER_NAME', 'localhost:5000')
db = SQLAlchemy(app)
redis_store = FlaskRedis(app)
from .model import *
api = FlaskJSONAPI(app, db)

from lxcp.lib import Lib, Data, User, Session, StrukAuth


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

@api.on_request.connect
def process_api_request(sender, method, endpoint, data, req_args):
    authorization = data.get('headers', {}).get('Authorization')
    if authorization:
        lib = Lib.get_lib()
        lib.session.node_auth(authorization)

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

#@app.route('/api/v1/data/<typ>')
#def api_v1_data_typ(typ):
#    lib = Lib.get_lib()
#    cls = Lib.CLASSES.get(typ)
#    if not cls:
#        return lib._fail()
#    if request.method == 'GET':
#        _id = request.args.get('id', type=int)
#        if _id:
#            return lib_render(lib.data_get(cls, _id))
#        else:
#            return lib_render(lib.data({typ: cls}))
#    elif request.method == 'POST':
#        pass

@app.route('/api/v1/data/<typ>')
def api_v1_data_typ(typ):
    response = api.serializer.get_collection(db.session, {}, typ)
    return jsonify(response.data)

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
    db = Lib.get_db()

    return render_template('setup.html', populated=db.is_db_populated())

@app.route('/setup/db_populate', methods=['POST'])
def db_populate():
    db = Lib.get_db()
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

@app.route('/res/')
def if_res():
    lib = Lib.get_lib()
    response = lib.data(classes=({'hosts':Host, 'containers':Container, 'nfs':NFS, 'groups':Group}))
    return render_template('res.html', **response)

@app.route('/containers/')
def if_containers():
    lib = Lib.get_lib()
    response = lib.data(classes=({'hosts':Host, 'containers':Container, 'nfs':NFS, 'groups':Group}))
    return render_template('containers.html', **response)

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == '__main__':
    app.run(debug=True)
