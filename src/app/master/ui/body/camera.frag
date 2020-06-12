#version 330 core
in vec2 UV;
uniform bool isWireframe;
out vec4 colour;

void main() {
    colour = vec4(0.168, 0.204, 0.231, 0.6);
}