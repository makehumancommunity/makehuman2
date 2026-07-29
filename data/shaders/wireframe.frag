#version 330 core
// needs a geometry shader before to calculate barycentric values

out vec4 FragColor;

in vec3 vBarycentric;
in vec3 vNormal; 

uniform vec4 wireframeColor = vec4(0.965, 0.565, 0.22, 1.0); // makehuman orange
uniform vec3 color = vec3(0.2, 0.2, 0.2);
uniform vec3 lightDir = normalize(vec3(0.5, 1.0, 0.3));   // just a global light vector
uniform float lineWidth = 0.7;                           // Wireframe thickness

void main() {
    // simple lighting
    float diffuse = max(dot(normalize(vNormal), lightDir), 0.0);

    // calculate screen-space wireframe edges

    vec3 dBarycentric = fwidth(vBarycentric);
    vec3 remapWidth = smoothstep(vec3(0.0), dBarycentric * lineWidth, vBarycentric);
    float edgeFactor = min(min(remapWidth.x, remapWidth.y), remapWidth.z);

    vec3 litMeshColor = color.rgb * (diffuse + 0.5); // color + some ambient extra light

    // layer the wireframe on top
    vec3 finalColor = vec3(mix(wireframeColor.rgb, litMeshColor, edgeFactor));
    FragColor = vec4(finalColor, 1.0);
}
