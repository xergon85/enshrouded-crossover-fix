#version 450
layout(vertices=3) out;
layout(location=0) in vec3 colorIn[];
layout(location=0) out vec3 colorOut[];
layout(location=1) patch out vec3 patchColor;
void main(){gl_out[gl_InvocationID].gl_Position=gl_in[gl_InvocationID].gl_Position;colorOut[gl_InvocationID]=colorIn[gl_InvocationID];if(gl_InvocationID==0){gl_TessLevelOuter[0]=1;gl_TessLevelOuter[1]=1;gl_TessLevelOuter[2]=1;gl_TessLevelInner[0]=1;patchColor=vec3(1);}}
