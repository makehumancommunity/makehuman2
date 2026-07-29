#version 330

layout (location = 0) in vec4 aPos;
layout (location = 1) in vec4 aNormal;
layout (location = 2) in vec2 aTexCoords;

uniform mat4 uMvpMatrix;
uniform mat4 uModelMatrix;
uniform mat4 uNormalMatrix;

out VS_OUT {
    vec3 FragPos;
    vec3 Normal;
    vec2 TexCoords;
} vs_out;

void main()
{
        vs_out.FragPos = vec3(uModelMatrix * aPos);
	vs_out.Normal = normalize(vec3(uNormalMatrix * aNormal));
	vs_out.TexCoords = aTexCoords;
	gl_Position = uMvpMatrix *  aPos;

}

