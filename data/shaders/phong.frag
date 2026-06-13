#version 330

// ─────────────────────────────────────────────────────────────────────
// Engine Shader Profile Pipeline Integration
// Core Architecture: MakeHuman 2 Standalone Pipeline BlackPunkduck
// Engineering, Modifications & Systems Integration: Elvaerwyn_MH2 2026 V1.1
// ─────────────────────────────────────────────────────────────────────

struct PointLight {
    vec3 position;
    vec3 color;
    float intensity;
    int type;
};

out vec4 FragColor;

in VS_OUT {
    vec3 FragPos;
    vec3 Normal;
    vec2 TexCoords;
} fs_in;

uniform sampler2D Texture;
uniform sampler2D AOTexture;
uniform PointLight pointLights[3];

// PORTED FROM PBR: Normal map sampler layout properties
uniform sampler2D NOTexture;
uniform float NoMult;


uniform vec3 lightWeight;
uniform vec4 ambientLight;
uniform vec3 viewPos;
uniform bool blinn;
uniform float AOMult;

// PORTED FROM PBR: High-quality normal valuation function
vec3 EvalNormal(vec3 n)
{
	vec3 no = texture(NOTexture, fs_in.TexCoords).rgb;

	no.r = 1.0 - no.r;
	no.g = 1.0 - no.g;

	no = normalize(no * 2.0 - 1.0);

	vec3 pos_dx = dFdx(fs_in.FragPos);
	vec3 pos_dy = dFdy(fs_in.FragPos);
	vec2 tex_dx = dFdx(fs_in.TexCoords);
	vec2 tex_dy = dFdy(fs_in.TexCoords);
	vec3 t = normalize(pos_dx * tex_dy.t - pos_dy * tex_dx.t);
	vec3 b = normalize(cross(n, t));

	mat3 TBN = mat3(t, b, n);
	no = normalize(mix(n, TBN * no, NoMult));
	return no;
}

void main()
{
	vec3 color = texture(Texture, fs_in.TexCoords).rgb;
	float transp = texture(Texture, fs_in.TexCoords).a;
	if (transp < 0.01) discard;

	float ao = texture(AOTexture, fs_in.TexCoords).r;

	// ambient
	vec3 ambient = ambientLight.rgb * vec3(ambientLight.a) * color;

	vec3 normal = normalize(fs_in.Normal);

	// PORTED FROM PBR: Swap smooth normal vector for evaluated normal map details
	if (NoMult > 0.05) {
		normal = EvalNormal(normal);
	}

	vec3 diffuse = vec3(0.0, 0.0, 0.0);
	vec3 specular = vec3(0.0, 0.0, 0.0);
	vec3 viewDir = normalize(viewPos - fs_in.FragPos);
	vec3 specw = vec3(lightWeight.x);

	for (int i = 0; i < 3; i++) {
		if (pointLights[i].intensity > 0.01) {
			// diffuse
			vec3 position = pointLights[i].position;
			vec3 L = vec3(0.0);
			float diff = 0.0;
                	float l = length(position - fs_in.FragPos) / pointLights[i].intensity;
			if (pointLights[i].type == 0) {
				L = normalize(position - fs_in.FragPos);
				diff = max(dot(L, normal), 0.0) / l;
			} else {
				L = normalize(position);
				diff = clamp(dot(L, normal), 0.0, 1.0) / 2.0;
			}
			diffuse += diff * pointLights[i].color * color;

			// specular
			float spec = 0.0;
			if(blinn) {
				vec3 halfwayDir = normalize(L + viewDir);
				spec = pow(max(dot(normal, halfwayDir), 0.0), lightWeight.y) / l;
			} else {
				vec3 reflectDir = reflect(-L, normal);
				spec = pow(max(dot(viewDir, reflectDir), 0.0), lightWeight.y) / l;
			}
			specular += specw * pointLights[i].color * spec;
		}
	}

	FragColor = vec4((ambient + diffuse + specular) * ao * AOMult, transp);
}

