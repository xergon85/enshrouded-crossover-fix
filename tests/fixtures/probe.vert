#version 450
layout(location=0) out vec3 col;
void main(){vec2 p[3]=vec2[](vec2(-.8,-.8),vec2(.8,-.8),vec2(0,.8));gl_Position=vec4(p[gl_VertexIndex%3],0,1);col=vec3(0,1,0);}
