import lxcp
import os

if __name__ == '__main__':
    if not lxcp.app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        lxcp.scheduler.start()
    app.config['SERVER_NAME'] = os.environ.get('FLASK_SERVER_NAME', 'localhost:5000')
    lxcp.app.run(debug=True)

