from flask import Flask, render_template, Response, send_file, request
from threading import Thread, Condition

from utility.setting import setting
from utility.define import UIEventType
from utility.jpeg_coder import jpeg_coder

from master.ui import ui


class StreamingServer(Thread):
    def __init__(self):
        super().__init__()
        self._buffer = None
        self._cond = Condition()
        self.start()

    def _get_buffer(self):
        self._cond.acquire()
        if self._buffer is None:
            self._cond.wait()

        camera_image = self._buffer
        self._buffer = None

        self._cond.release()
        return camera_image

    def set_buffer(self, camera_image):
        self._cond.acquire()
        self._buffer = camera_image
        self._cond.notify()
        self._cond.release()

    def run(self):
        app = Flask('StreamingServer', template_folder='master/streaming')

        @app.route('/')
        def index():
            cameras = enumerate(setting.get_working_camera_ids())
            return render_template('index.html', cameras=cameras)

        @app.route('/style.css')
        def scss():
            return send_file('master/streaming/style.css')

        @app.route('/normalize.css')
        def ncss():
            return send_file('master/streaming/normalize.css')

        @app.route('/activate')
        def activate():
            camera_id = request.args.get('camera_id')

            ui.dispatch_event(
                UIEventType.CLOSEUP_CAMERA,
                camera_id
            )

            return f'activate {camera_id}'

        @app.route('/focus')
        def focus():
            toggle = request.args.get('toggle')
            toggle = toggle == 'true'

            ui.dispatch_event(
                UIEventType.CAMERA_FOCUS,
                toggle
            )

            return f'focus {toggle}'

        def getImage():
            while True:
                image = self._get_buffer()
                if image is None:
                    continue
                data = jpeg_coder.encode(image, quality=70)
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' +
                    data + b'\r\n'
                )

        @app.route('/video_feed')
        def video_feed():
            return Response(
                getImage(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )

        @app.after_request
        def add_header(r):
            r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            r.headers["Pragma"] = "no-cache"
            r.headers["Expires"] = "0"
            r.headers['Cache-Control'] = 'public, max-age=0'
            return r

        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.run(host='0.0.0.0', port=80)
