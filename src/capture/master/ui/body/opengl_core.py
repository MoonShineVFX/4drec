from PyQt5.Qt import (
    QSize, Qt, QOpenGLWidget, QSurfaceFormat
)

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GL.shaders import *

import math

from utility.repeater import Repeater

from .opengl_components import (
    OpenGLCamera, OpenGLObject, FloorObject, CameraObject
)


class OpenGLCore(QOpenGLWidget):
    _rot_speed = 0.5
    _offset_speed = 0.0035
    _zoom_wheel_speed = 0.2
    _zoom_move_speed = 0.01
    _default_shader_parms = {
        'gamma': 1.5,
        'saturate': 1.2,
        'exposure': 1.5
    }

    def __init__(self, parent, interface):
        super().__init__(parent)
        self._interface = interface

        # UI
        self._last_mouse_pos = None
        self._window_size = None
        self._background_color = None
        self._shader_parms = self._default_shader_parms.copy()

        # GL
        self._objects = {}

        self._setup_ui()

        self._camera = OpenGLCamera(
            self._window_size[0] / self._window_size[1]
        )
        self._camera.on_update(self._on_camera_update)

        self._repeater = None

    def _setup_ui(self):
        self._window_size = (
            self.parentWidget().width(),
            self.parentWidget().height()
        )
        color = self.palette().dark().color()
        self._background_color = color.getRgbF()

        # anti aliasing
        fmt = QSurfaceFormat()
        fmt.setSamples(8)
        self.setFormat(fmt)

    @staticmethod
    def load_shader(filename):
        with open(f'master/ui/body/{filename}') as f:
            return f.read()

    def set_geo(self, cache, turntable=0):
        obj = self._objects['main']
        if cache is None:
            # clean empty
            if not obj.is_empty():
                self._interface.update_vertex_count(0)
                obj.update()
                self.update()
            return
        elif cache[2] is None:
            # camera rig geo
            self._objects['camera'].update(cache[0], cache[1][0])
            return

        obj.update(
            vertex_count=cache[0],
            pos_list=cache[1][0],
            uv_list=cache[1][1],
            texture=cache[2],
            resolution=cache[3]
        )
        self._interface.update_vertex_count(cache[0])

        # turntable
        if turntable != 0:
            self._camera.offset_rot(
                0,
                turntable
            )
            self._camera.update()

        self.update()

    def toggle_wireframe(self, is_wireframe):
        for obj in self._objects.values():
            obj.set_wireframe(is_wireframe)
        self.update()

    def toggle_rig(self, is_rig):
        for name in ('floor', 'camera'):
            self._objects[name].set_visible(is_rig)
        self._objects['main'].set_backfacing(is_rig)
        self.update()

    def sizeHint(self):
        return QSize(*self._window_size)

    def resizeGL(self, width, height):
        self._window_size = (width, height)
        self._camera.set_aspect(
            self._window_size[0] / self._window_size[1]
        )
        self._camera.update()
        self.update()

    def mousePressEvent(self, event):
        buttons = event.buttons()

        if buttons & Qt.LeftButton:
            self.setCursor(Qt.SizeAllCursor)
        elif buttons & Qt.MidButton:
            self.setCursor(Qt.OpenHandCursor)
        elif buttons & Qt.RightButton:
            self.setCursor(Qt.SizeVerCursor)

        self._last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        buttons = event.buttons()
        if not buttons:
            return

        dx = event.x() - self._last_mouse_pos.x()
        dy = event.y() - self._last_mouse_pos.y()

        if dx == 0 and dy == 0:
            return

        if buttons & Qt.LeftButton:
            self._camera.offset_rot(
                dy * self._rot_speed,
                dx * self._rot_speed
            )
        elif buttons & Qt.MidButton:
            self._camera.offset_pos(
                dx * self._offset_speed,
                -dy * self._offset_speed
            )
        elif buttons & Qt.RightButton:
            self._camera.offset_zoom(
                dy * self._zoom_move_speed
            )

        self._last_mouse_pos = event.pos()
        self._camera.update()
        self.update()

    def mouseReleaseEvent(self, event):
        self.unsetCursor()

    def wheelEvent(self, event):
        delta = math.copysign(1, event.angleDelta().y())
        self._camera.offset_zoom(
            delta * self._zoom_wheel_speed
        )
        self._camera.update()
        self.update()
        event.accept()

    def reset_camera_transform(self):
        self._camera.reset()
        self._camera.update()
        self.update()

    def offset_model_shader(self, parm_name, value):
        self._shader_parms[parm_name] += value
        self._objects['main'].set_shader_parm(
            parm_name, self._shader_parms[parm_name]
        )
        self.update()
        self._interface.update_parm(
            parm_name, self._shader_parms[parm_name]
        )

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(*self._background_color)

        # Shaders
        vtx = compileShader(
            self.load_shader('standard.vert'), GL_VERTEX_SHADER
        )
        main = compileShader(
            self.load_shader('main.frag'), GL_FRAGMENT_SHADER
        )
        circle = compileShader(
            self.load_shader('circle.frag'), GL_FRAGMENT_SHADER
        )
        camera = compileShader(
            self.load_shader('camera.frag'), GL_FRAGMENT_SHADER
        )

        # Objects
        self._objects['main'] = OpenGLObject(vtx, main, has_texture=True)
        self._objects['floor'] = FloorObject(vtx, circle)
        self._objects['camera'] = CameraObject(vtx, camera)

        # Set shader default
        for key, value in self._shader_parms.items():
            self._objects['main'].set_shader_parm(
                key, value
            )

    def paintGL(self):
        for obj in self._objects.values():
            if obj.is_visible():
                obj.render()

    def _on_camera_update(self, project_matrix, move_matrix):
        for obj in self._objects.values():
            obj.update_camera(project_matrix, move_matrix)
