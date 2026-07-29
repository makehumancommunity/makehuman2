#version 330 core
layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

// Input from Vertex Shader (Object or World Space positions)
in VS_OUT {
    vec3 FragPos;
    vec3 Normal;
    vec2 TexCoords;
} fs_in[];

out vec3 vBarycentric;
out vec3 vNormal;

void main() {
    // Calculate the face normal using cross product of triangle edges
    vec3 edge1 = vec3 (gl_in[1].gl_Position - gl_in[0].gl_Position); 
    vec3 edge2 = vec3 (gl_in[2].gl_Position - gl_in[0].gl_Position);
    vec3 faceNormal = normalize(cross(edge1, edge2));

    for(int i = 0; i < 3; ++i) {
        gl_Position = gl_in[i].gl_Position;
        vNormal = faceNormal;
        
        // Assign barycentric anchors per vertex
        vBarycentric = vec3(0.0, 0.0, 0.0);
        vBarycentric[i] = 1.0; 
        EmitVertex();
    }
    EndPrimitive();
}
