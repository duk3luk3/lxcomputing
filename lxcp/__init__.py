#! python

from flask import Flask, g, jsonify, abort, redirect, url_for, make_response, render_template, request, session, send_from_directory, current_app
from flask.json import JSONEncoder
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_jsonapi import FlaskJSONAPI
from flask_apscheduler import APScheduler
import os
import sys


from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
#        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'stream': sys.stderr,
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})


app = Flask(__name__)
DBFILE = os.environ.get('FLASK_DBFILE', '/srv/lxcompute/lxcompute.sqlite3')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DBFILE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DBFILE
app.config['LXKEY'] = os.environ.get('FLASK_LXKEY')
app.config['LXCERT'] = os.environ.get('FLASK_LXCERT')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SCHEDULER_JOBS'] = [
        {
            'id': 'cont_schedule',
            'func': 'lxcp.schedule:cont_schedule',
            'trigger': 'interval',
            'minutes': 2
        }
]
app.config['LXCP_INSTANCES'] = [
        {
            'name': 'balanced.micro',
            'cpu': 2,
            'ram': 2
        },
        {
            'name': 'balanced.std',
            'cpu': 8,
            'ram': 8
        },
        {
            'name': 'balanced.big',
            'cpu': 16,
            'ram': 16
        },
        {
            'name': 'balanced.max',
            'cpu': 32,
            'ram': 32
        },
        {
            'name': 'mem.std',
            'cpu': 8,
            'ram': 16
        },
        {
            'name': 'mem.big',
            'cpu': 16,
            'ram': 32
        },
        {
            'name': 'mem.max',
            'cpu': 32,
            'ram': 64
        },
        {
            'name': 'cpu.micro',
            'cpu': 8,
            'ram': 4
        },
        {
            'name': 'cpu.std',
            'cpu': 16,
            'ram': 8
        }
]
#app.config['SCHEDULER_API_ENABLED'] = True
db = SQLAlchemy(app)
from .model import *
api = FlaskJSONAPI(app, db)
scheduler = APScheduler(app=app)

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

#@api.on_request.connect
#def process_api_request(sender, method, endpoint, data, req_args):
#    authorization = data.get('headers', {}).get('Authorization')
#    if not authorization:
#        authorization = request.headers.get('Authorization')
#    print('Auth:', authorization)
#    if authorization and authorization != 'foobar':
#        lib = Lib.get_lib()
#        lib.session.node_auth(authorization)

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
    password = request.form.get('password')
    impersonate = request.form.get('impersonate')

    target = request.form.get('next', 'index')

    lib.login(username, password, impersonate)
    return redirect(url_for(target))

@app.route('/logout')
def logout():
    user_session = Session(session)
    user_session.clear_login()

    return redirect('/')

@app.route('/unpersonate')
def unpersonate():
    user_session = Session(session)
    user_session.clear_impersonation()

    target = request.args.get('next', 'index')

    return redirect(url_for(target))

@app.route('/setup')
def setup():
    db = Lib.get_db()

    lib = Lib.get_lib()

    client = lib.lxclient
    client.client_connect()

    images = client.images(None)
    response = lib.data(classes=({'hosts':Host, 'containers':Container}))

    return render_template('setup.html', populated=db.is_db_populated(), images=images, **response)

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

@app.route('/setup/container_provision', methods=['POST'])
def container_provision():
    lib = Lib.get_lib()
    container_id = int(request.form['container_id'])
    lib.container_provision(container_id)
    return redirect('/setup')

@app.route('/setup/lxc_trust', methods=['POST'])
def lxc_trust():
    lib = Lib.get_lib()
    client = lib.lxclient

    trust_pw = request.form['trust_pw']
    client.client_trust(trust_pw, None)
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
    response = lib.data(classes=({'hosts':Host, 'containers':Container, 'nfs':NFS, 'groups':Group, 'slots': Slot}))
    client = lib.lxclient
    images = client.images(None)
    config = current_app.config
    return render_template('containers.html', images=images, **response)

@app.route('/schedule/')
def if_schedule():
    lib = Lib.get_lib()
    response = lib.data(classes=({'hosts':Host, 'containers':Container, 'nfs':NFS, 'groups':Group, 'slots': Slot}))
    client = lib.lxclient
    images = client.images(None)
    config = current_app.config
    return render_template('scheduling.html', images=images, instances=config['LXCP_INSTANCES'], **response)

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True, use_reloader=False)
