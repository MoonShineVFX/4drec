#version 330 core
in vec2 UV;
uniform sampler2D inTexture;
uniform bool isWireframe;
uniform bool isShowBackFacing;
uniform float gamma = 1.0;
uniform float saturate = 1.0;
uniform float exposure = 1.0;
out vec4 colour;
const float Epsilon = 1e-10;

vec3 RGBtoHSV(in vec3 RGB)
{
    vec4  P   = (RGB.g < RGB.b) ? vec4(RGB.bg, -1.0, 2.0/3.0) : vec4(RGB.gb, 0.0, -1.0/3.0);
    vec4  Q   = (RGB.r < P.x) ? vec4(P.xyw, RGB.r) : vec4(RGB.r, P.yzx);
    float C   = Q.x - min(Q.w, Q.y);
    float H   = abs((Q.w - Q.y) / (6.0 * C + Epsilon) + Q.z);
    vec3  HCV = vec3(H, C, Q.x);
    float S   = HCV.y / (HCV.z + Epsilon);
    return vec3(HCV.x, S, HCV.z);
}

vec3 HSVtoRGB(in vec3 HSV)
{
    float H   = HSV.x;
    float R   = abs(H * 6.0 - 3.0) - 1.0;
    float G   = 2.0 - abs(H * 6.0 - 2.0);
    float B   = 2.0 - abs(H * 6.0 - 4.0);
    vec3  RGB = clamp( vec3(R,G,B), 0.0, 1.0 );
    return ((RGB - 1.0) * HSV.y + 1.0) * HSV.z;
}

void main() {
  if (isWireframe) {
    colour = vec4(1.0);
  } else if (!gl_FrontFacing && isShowBackFacing) {
  	colour = vec4(0.0, 1.0, 0.0, 1.0);
  } else {
    vec4 texColor = texture(inTexture, UV);
    vec3 hsv = RGBtoHSV(texColor.rgb);
    hsv.y *= saturate;
    vec3 srgb = HSVtoRGB(hsv.rgb);
    colour = vec4(srgb, 1.0);
    colour = pow(colour, vec4(gamma));
    colour *= exposure;
    colour.a = 1.0;
  }
}