import lxcp
import os

if __name__ == '__main__':
    if not lxcp.app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        lxcp.scheduler.start()
    lxcp.app.run(debug=True)

