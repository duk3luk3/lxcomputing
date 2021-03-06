import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
activate_this = path + '/.venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

sys.path.insert(0, path)


def application(environ, start_response):
    for key, value in environ.items():
        if key.startswith('FLASK_'):
            os.environ[key] = value
    from lxcp import app
    app.config['SERVER_NAME'] = environ.get('HTTP_HOST', environ['SERVER_NAME'])
    app.config['PREFERRED_URL_SCHEME'] = environ.get('wsgi.url_scheme')
    return app.wsgi_app(environ, start_response)
