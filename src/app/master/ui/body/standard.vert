#version 330 core
in vec3 vert;
in vec2 uV;
uniform mat4 moveMatrix;
uniform mat4 projectMatrix;
uniform mat4 modelMatrix = mat4(1.0);
out vec2 UV;

void main() {
  gl_Position = projectMatrix * moveMatrix * modelMatrix * vec4(vert, 1.0);
  UV = uV;
}