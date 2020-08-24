#version 330 core
in vec2 UV;
uniform sampler2D inTexture;
uniform bool isWireframe;
uniform bool isShowBackFacing;
uniform float gammaCorrect = 1.0;
out vec4 colour;

void main() {
  if (isWireframe) {
    colour = vec4(1.0);
  } else if (!gl_FrontFacing && isShowBackFacing) {
  	colour = vec4(0.0, 1.0, 0.0, 1.0);
  } else {
    colour = texture(inTexture, UV).rgba;
    colour = pow(colour, vec4(gammaCorrect));
  }
}