from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GL.shaders import *

import glm
import numpy as np
import math


class OpenGLCamera():
    _default_zoom = -2.0
    _default_pos = [0.0, -0.8]

    def __init__(self, aspect):
        self._matrix = None

        self._rot_x = 0
        self._rot_y = 0
        self._zoom = self._default_zoom
        self._pos = self._default_pos.copy()
        self._aspect = aspect

        self._callbacks = []

        self._initialize()

    @staticmethod
    def normalize_angle(angle):
        while angle < 0:
            angle += 360
        while angle > 360:
            angle -= 360
        return angle

    def _initialize(self):
        fov = math.radians(45)
        f = 1.0 / math.tan(fov / 2.0)
        z_near = 0.01
        z_far = 1000.0
        self._matrix = np.array([
            f, 0.0, 0.0, 0.0,
            0.0, f, 0.0, 0.0,
            0.0, 0.0, (z_far + z_near) / (z_near - z_far), -1.0,
            0.0, 0.0, 2.0 * z_far * z_near / (z_near - z_far), 0.0
        ], np.float32)

    def update(self):
        project_matrix = np.copy(self._matrix)
        project_matrix[0] /= self._aspect

        move_matrix = glm.mat4(1.0)
        move_matrix = glm.translate(move_matrix, glm.vec3(*self._pos, self._zoom))
        move_matrix = glm.rotate(
            move_matrix, math.radians(self._rot_x), (1.0, 0.0, 0.0)
        )
        move_matrix = glm.rotate(
            move_matrix, math.radians(self._rot_y), (0.0, 1.0, 0.0)
        )

        for func in self._callbacks:
            func(project_matrix, move_matrix)

    def on_update(self, func):
        self._callbacks.append(func)

    def offset_rot(self, x, y):
        new_x_rot = self._rot_x + x
        new_y_rot = self._rot_y + y
        self._rot_x = self.normalize_angle(new_x_rot)
        self._rot_y = self.normalize_angle(new_y_rot)

    def offset_pos(self, x, y):
        self._pos[0] += x
        self._pos[1] += y

    def offset_zoom(self, z):
        self._zoom += z

    def set_aspect(self, aspect):
        self._aspect = aspect

    def reset(self):
        self._rot_x = 0
        self._rot_y = 0
        self._zoom = self._default_zoom
        self._pos = self._default_pos.copy()


class OpenGLProgram():
    def __init__(self, vertex_shader, fragment_shader):
        self._program = compileProgram(vertex_shader, fragment_shader)

    def use(self):
        glUseProgram(self._program)

    def attr(self, name):
        return glGetAttribLocation(self._program, name)

    def set_wireframe(self, toggle):
        self.use()
        uni_wireframe = glGetUniformLocation(
            self._program, 'isWireframe'
        )
        glUniform1i(uni_wireframe, toggle)

    def set_backfacing(self, toggle):
        self.use()
        uni_backfacing = glGetUniformLocation(
            self._program, 'isShowBackFacing'
        )
        glUniform1i(uni_backfacing, toggle)

    def set_parm(self, parm_name, value):
        self.use()
        gl_parm = glGetUniformLocation(
            self._program, parm_name
        )
        glUniform1f(gl_parm, value)

    def update_camera(self, project_matrix, move_matrix):
        self.use()
        uni_move_matrix = glGetUniformLocation(self._program, 'moveMatrix')
        uni_proj_matrix = glGetUniformLocation(self._program, 'projectMatrix')
        glUniformMatrix4fv(
            uni_move_matrix, 1, GL_FALSE, glm.value_ptr(move_matrix)
        )
        glUniformMatrix4fv(uni_proj_matrix, 1, GL_FALSE, project_matrix)

    def update_transform(self, matrix):
        self.use()
        uni_model_matrix = glGetUniformLocation(self._program, 'modelMatrix')
        glUniformMatrix4fv(uni_model_matrix, 1, GL_FALSE, matrix)


class OpenGLObject():
    def __init__(
        self, vertex_shader, fragment_shader,
        has_texture=False, has_wireframe=True, has_uv=True
    ):
        self._program = OpenGLProgram(vertex_shader, fragment_shader)
        self.update_camera = self._program.update_camera
        self._visible = True

        self._vao = None
        self._buffer_vertex = None
        self._buffer_uv = None

        self._texture_id = None
        self._is_wireframe = False

        self._has_texture = has_texture
        self._has_wireframe = has_wireframe
        self._has_uv = has_uv

        self._vertex_count = 0

        self._texture_resolution = 4096

        self._initialize()

    def _initialize(self):
        # geo
        self._vao = glGenVertexArrays(1)
        glBindVertexArray(self._vao)

        self._buffer_vertex = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._buffer_vertex)
        glEnableVertexAttribArray(self._program.attr('vert'))
        glVertexAttribPointer(
            self._program.attr('vert'), 3, GL_FLOAT, GL_FALSE, 0, None
        )

        if self._has_uv:
            self._buffer_uv = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self._buffer_uv)
            glEnableVertexAttribArray(self._program.attr('uV'))
            glVertexAttribPointer(
                self._program.attr('uV'), 2, GL_FLOAT, GL_FALSE, 0, None
            )

        # texture
        if self._has_texture:
            self._program.use()
            glUniform1i(self._program.attr('inTexture'), 0)
            self._texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self._texture_id)

            # GL_NEAREST or GL_LINEAR
            glTexParameterf(
                GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR
            )
            glTexParameterf(
                GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR
            )
            glTexImage2D(
                GL_TEXTURE_2D, 0, 3,
                self._texture_resolution, self._texture_resolution,
                0, GL_RGB, GL_UNSIGNED_BYTE,
                np.zeros(
                    [self._texture_resolution, self._texture_resolution, 3],
                    dtype=np.uint8
                )
            )

    def update(
        self, vertex_count=0, pos_list=None, uv_list=None, texture=None, resolution=4096
    ):
        # geo
        self._vertex_count = vertex_count

        if self._vertex_count == 0:
            return

        glBindBuffer(GL_ARRAY_BUFFER, self._buffer_vertex)
        glBufferData(
            GL_ARRAY_BUFFER, 4 * 3 * len(pos_list), pos_list,
            GL_STATIC_DRAW
        )

        if self._has_uv:
            glBindBuffer(GL_ARRAY_BUFFER, self._buffer_uv)
            glBufferData(
                GL_ARRAY_BUFFER, 4 * 2 * len(uv_list), uv_list,
                GL_STATIC_DRAW
            )

        # texture
        if self._has_texture:
            glBindTexture(GL_TEXTURE_2D, self._texture_id)
            if resolution != self._texture_resolution:
                self._texture_resolution = resolution
                glTexImage2D(
                    GL_TEXTURE_2D,
                    0,
                    3,
                    self._texture_resolution,
                    self._texture_resolution,
                    0, GL_RGB, GL_UNSIGNED_BYTE,
                    texture
                )
            else:
                glTexSubImage2D(
                    GL_TEXTURE_2D,
                    0,
                    0,
                    0,
                    self._texture_resolution,
                    self._texture_resolution,
                    GL_RGB,
                    GL_UNSIGNED_BYTE,
                    texture
                )

    def render(self):
        if self._vertex_count == 0:
            return

        self._program.use()
        self._program.set_wireframe(False)

        if self._has_texture:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self._texture_id)

        glBindVertexArray(self._vao)
        glDrawArrays(GL_TRIANGLES, 0, self._vertex_count)

        if self._is_wireframe and self._has_wireframe:
            self._program.set_wireframe(True)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glDrawArrays(GL_TRIANGLES, 0, self._vertex_count)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def is_empty(self):
        return self._vertex_count == 0

    def is_visible(self):
        return self._visible

    def set_wireframe(self, toggle):
        if self._has_wireframe:
            self._is_wireframe = toggle

    def set_backfacing(self, toggle):
        self._program.set_backfacing(toggle)

    def set_transform(self, matrix):
        self._program.update_transform(matrix)

    def set_visible(self, visible):
        self._visible = visible

    def set_shader_parm(self, parm_name, value):
        self._program.set_parm(parm_name, value)


class FloorObject(OpenGLObject):
    def __init__(self, vertex_shader, fragment_shader):
        super().__init__(
            vertex_shader, fragment_shader,
            has_wireframe=False
        )
        self._build_geo()
        self._visible = False

    def _build_geo(self):
        pos_list = np.array(
            [
                (-1, 0, 1), (1, 0, 1), (-1, 0, -1),
                (-1, 0, -1), (1, 0, 1), (1, 0, -1)
            ],
            np.float32
        )
        pos_list *= 1.5

        uv_list = np.array(
            [
                (0, 0), (1, 0), (0, 1),
                (0, 1), (1, 0), (1, 1)
            ],
            np.float32
        )

        self.update(len(pos_list), pos_list, uv_list)


class CameraObject(OpenGLObject):
    def __init__(self, vertex_shader, fragment_shader):
        super().__init__(
            vertex_shader, fragment_shader,
            has_wireframe=False, has_uv=False
        )
        self._visible = False
