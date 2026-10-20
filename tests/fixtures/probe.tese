#version 450
layout(triangles,equal_spacing,ccw) in;
layout(location=0) in vec3 colors[];
layout(location=1) patch in vec3 patchColor;
layout(location=0) out vec3 color;
void main(){gl_Position=gl_TessCoord.x*gl_in[0].gl_Position+gl_TessCoord.y*gl_in[1].gl_Position+gl_TessCoord.z*gl_in[2].gl_Position;color=patchColor*(gl_TessCoord.x*colors[0]+gl_TessCoord.y*colors[1]+gl_TessCoord.z*colors[2]);}
