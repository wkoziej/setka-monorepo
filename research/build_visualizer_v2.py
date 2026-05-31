"""V2 — klarowny rytm 120BPM, dramatyczny beat-punch. Render klatek na-beacie vs miedzy
=> dowod sync z danych (rdzen/pierscien duzy na beacie, maly miedzy)."""
import json, socket, sys

def send(code, t=180):
    req = json.dumps({"type": "execute", "code": code, "strict_json": False}) + "\0"
    with socket.socket() as s:
        s.settimeout(t); s.connect(("localhost", 9876)); s.sendall(req.encode())
        buf = bytearray()
        while True:
            c = s.recv(65536)
            if not c: break
            buf.extend(c)
            if b"\0" in buf: break
    r = json.loads(bytes(buf).partition(b"\0")[0].decode())
    if r.get("status") != "ok":
        print("  !! ERROR:", str(r.get("message"))[:1500]); sys.exit(1)
    return r.get("result")

ANALYSIS = "/Users/wokoziej/dev/setka-monorepo/research/audio/analysis/beat_120bpm_12s_analysis.json"

stage_a = r'''
import bpy, json, numpy as np
d = json.load(open("%s")); fb=d["frequency_bands"]; ae=d["animation_events"]
times=np.array(fb["times"],float); dt=float(times[1]-times[0]); N=len(times)
def norm(a):
    a=np.array(a,float); p=np.percentile(a,99); return (np.clip(a/p,0,1) if p>0 else np.zeros_like(a)).astype(np.float32)
bass_n,mid_n,high_n=norm(fb["bass_energy"]),norm(fb["mid_energy"]),norm(fb["high_energy"])
def env(events, decay):
    e=np.zeros(N,np.float32)
    for t in events:
        i=int(round(t/dt))
        for k in range(0,int(decay/dt)+1):
            j=i+k
            if 0<=j<N: e[j]=max(e[j],1.0-k*dt/decay)
    return e
beat_env=env(ae.get("beats",[]),0.13); peak_env=env(ae.get("energy_peaks",[]),0.25)
for c in list(bpy.data.collections):
    if c.name=="cymatic_viz":
        for o in list(c.objects): bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(c)
coll=bpy.data.collections.new("cymatic_viz"); bpy.context.scene.collection.children.link(coll)
me=bpy.data.meshes.new("audio_data"); me.vertices.add(N)
co=np.zeros(N*3,np.float32); co[0::3]=np.arange(N,dtype=np.float32)*dt; me.vertices.foreach_set("co",co)
for name,arr in [("bass_n",bass_n),("mid_n",mid_n),("high_n",high_n),("beat_env",beat_env),("peak_env",peak_env)]:
    a=me.attributes.new(name=name,type='FLOAT',domain='POINT'); a.data.foreach_set("value",arr)
me.update()
obj=bpy.data.objects.new("audio_data",me); coll.objects.link(obj); obj.hide_render=True; obj.hide_viewport=True
sc=bpy.context.scene; sc.render.fps=30; sc.frame_start=1; sc.frame_end=int(d["duration"]*30)
sc.render.resolution_x=1280; sc.render.resolution_y=720
try: sc.render.engine='BLENDER_EEVEE_NEXT'
except Exception: sc.render.engine='BLENDER_EEVEE'
w=bpy.data.worlds.get("cymatic_world") or bpy.data.worlds.new("cymatic_world"); w.use_nodes=True
bg=w.node_tree.nodes.get("Background")
if bg: bg.inputs[0].default_value=(0.01,0.01,0.02,1); bg.inputs[1].default_value=0.25
sc.world=w
result={"N":N,"beats":len(ae["beats"]),"frame_end":sc.frame_end}
''' % ANALYSIS

stage_b = r'''
import bpy, math
coll=bpy.data.collections["cymatic_viz"]; audio=bpy.data.objects["audio_data"]; DT=%f
M=128; STRIDE=0.045

def band_field(nd,lk,attr,with_beat):
    idx=nd.new('GeometryNodeInputIndex'); st=nd.new('GeometryNodeInputSceneTime')
    offs=nd.new('ShaderNodeMath'); offs.operation='MULTIPLY'; offs.inputs[1].default_value=STRIDE; lk.new(idx.outputs['Index'],offs.inputs[0])
    tsec=nd.new('ShaderNodeMath'); tsec.operation='SUBTRACT'; lk.new(st.outputs['Seconds'],tsec.inputs[0]); lk.new(offs.outputs[0],tsec.inputs[1])
    sidx=nd.new('ShaderNodeMath'); sidx.operation='DIVIDE'; sidx.inputs[1].default_value=DT; lk.new(tsec.outputs[0],sidx.inputs[0])
    flo=nd.new('ShaderNodeMath'); flo.operation='FLOOR'; lk.new(sidx.outputs[0],flo.inputs[0])
    oi=nd.new('GeometryNodeObjectInfo'); oi.inputs['Object'].default_value=audio; oi.transform_space='ORIGINAL'
    na=nd.new('GeometryNodeInputNamedAttribute'); na.data_type='FLOAT'; na.inputs['Name'].default_value=attr
    si=nd.new('GeometryNodeSampleIndex'); si.data_type='FLOAT'; si.domain='POINT'; si.clamp=True
    lk.new(oi.outputs['Geometry'],si.inputs['Geometry']); lk.new(na.outputs['Attribute'],si.inputs['Value']); lk.new(flo.outputs[0],si.inputs['Index'])
    out=si
    if with_beat:  # global beat punch: + beat_env(current time) * 3
        sidx0=nd.new('ShaderNodeMath'); sidx0.operation='DIVIDE'; sidx0.inputs[1].default_value=DT; lk.new(st.outputs['Seconds'],sidx0.inputs[0])
        flo0=nd.new('ShaderNodeMath'); flo0.operation='FLOOR'; lk.new(sidx0.outputs[0],flo0.inputs[0])
        nb=nd.new('GeometryNodeInputNamedAttribute'); nb.data_type='FLOAT'; nb.inputs['Name'].default_value="beat_env"
        sb=nd.new('GeometryNodeSampleIndex'); sb.data_type='FLOAT'; sb.domain='POINT'; sb.clamp=True
        lk.new(oi.outputs['Geometry'],sb.inputs['Geometry']); lk.new(nb.outputs['Attribute'],sb.inputs['Value']); lk.new(flo0.outputs[0],sb.inputs['Index'])
        bp=nd.new('ShaderNodeMath'); bp.operation='MULTIPLY'; bp.inputs[1].default_value=3.0; lk.new(sb.outputs[0],bp.inputs[0])
        add=nd.new('ShaderNodeMath'); add.operation='ADD'; lk.new(si.outputs[0],add.inputs[0]); lk.new(bp.outputs[0],add.inputs[1]); out=add
    return out

def ring(name,attr,radius,zcol):
    ng=bpy.data.node_groups.new(name,'GeometryNodeTree')
    ng.interface.new_socket("Geometry",in_out='INPUT',socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry",in_out='OUTPUT',socket_type='NodeSocketGeometry')
    nd,lk=ng.nodes,ng.links; gout=nd.new('NodeGroupOutput')
    circ=nd.new('GeometryNodeMeshCircle'); circ.fill_type='NONE'; circ.inputs['Vertices'].default_value=M; circ.inputs['Radius'].default_value=radius
    cube=nd.new('GeometryNodeMeshCube'); cube.inputs['Size'].default_value=(0.18,0.18,1.0)
    iop=nd.new('GeometryNodeInstanceOnPoints'); lk.new(circ.outputs['Mesh'],iop.inputs['Points']); lk.new(cube.outputs['Mesh'],iop.inputs['Instance'])
    h=band_field(nd,lk,attr,True)
    hsc=nd.new('ShaderNodeMath'); hsc.operation='MULTIPLY_ADD'; hsc.inputs[1].default_value=5.0; hsc.inputs[2].default_value=0.1; lk.new(h.outputs[0],hsc.inputs[0])
    comb=nd.new('ShaderNodeCombineXYZ'); comb.inputs['X'].default_value=1; comb.inputs['Y'].default_value=1; lk.new(hsc.outputs[0],comb.inputs['Z'])
    scl=nd.new('GeometryNodeScaleInstances'); lk.new(iop.outputs['Instances'],scl.inputs['Instances']); lk.new(comb.outputs[0],scl.inputs['Scale'])
    setm=nd.new('GeometryNodeSetMaterial'); lk.new(scl.outputs[0],setm.inputs['Geometry'])
    mat=bpy.data.materials.new(name+"_m"); mat.use_nodes=True; mt=mat.node_tree; mt.nodes.clear()
    out=mt.nodes.new('ShaderNodeOutputMaterial'); em=mt.nodes.new('ShaderNodeEmission')
    geo=mt.nodes.new('ShaderNodeNewGeometry'); sep=mt.nodes.new('ShaderNodeSeparateXYZ'); mr=mt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value=0; mr.inputs['From Max'].default_value=6; ramp=mt.nodes.new('ShaderNodeValToRGB')
    e=ramp.color_ramp.elements; e[0].position=0; e[0].color=zcol[0]; e[1].position=1; e[1].color=zcol[1]
    mt.links.new(geo.outputs['Position'],sep.inputs['Vector']); mt.links.new(sep.outputs['Z'],mr.inputs['Value']); mt.links.new(mr.outputs['Result'],ramp.inputs['Fac'])
    mt.links.new(ramp.outputs['Color'],em.inputs['Color']); em.inputs['Strength'].default_value=4.0; mt.links.new(em.outputs['Emission'],out.inputs['Surface'])
    setm.inputs['Material'].default_value=mat; lk.new(setm.outputs['Geometry'],gout.inputs[0])
    o=bpy.data.objects.new(name,bpy.data.meshes.new(name)); coll.objects.link(o); o.modifiers.new("gn",'NODES').node_group=ng

ring("viz_bass","bass_n",5.0,[(0.0,0.2,1.0,1),(0.2,0.9,1.0,1)])
ring("viz_mid","mid_n",6.4,[(0.0,1.0,0.4,1),(1.0,1.0,0.2,1)])
ring("viz_high","high_n",7.8,[(1.0,0.3,0.6,1),(1.0,0.9,0.9,1)])

# core: scale = 0.5 + beat_env*3 (dramatyczny puls)
ng2=bpy.data.node_groups.new("viz_core_gn",'GeometryNodeTree')
ng2.interface.new_socket("Geometry",in_out='INPUT',socket_type='NodeSocketGeometry')
ng2.interface.new_socket("Geometry",in_out='OUTPUT',socket_type='NodeSocketGeometry')
nd,lk=ng2.nodes,ng2.links; gout=nd.new('NodeGroupOutput')
ico=nd.new('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value=1.0; ico.inputs['Subdivisions'].default_value=3
st=nd.new('GeometryNodeInputSceneTime'); sidx=nd.new('ShaderNodeMath'); sidx.operation='DIVIDE'; sidx.inputs[1].default_value=DT; lk.new(st.outputs['Seconds'],sidx.inputs[0])
flo=nd.new('ShaderNodeMath'); flo.operation='FLOOR'; lk.new(sidx.outputs[0],flo.inputs[0])
oi=nd.new('GeometryNodeObjectInfo'); oi.inputs['Object'].default_value=audio; oi.transform_space='ORIGINAL'
na=nd.new('GeometryNodeInputNamedAttribute'); na.data_type='FLOAT'; na.inputs['Name'].default_value="beat_env"
si=nd.new('GeometryNodeSampleIndex'); si.data_type='FLOAT'; si.domain='POINT'; si.clamp=True
lk.new(oi.outputs['Geometry'],si.inputs['Geometry']); lk.new(na.outputs['Attribute'],si.inputs['Value']); lk.new(flo.outputs[0],si.inputs['Index'])
sc2=nd.new('ShaderNodeMath'); sc2.operation='MULTIPLY_ADD'; sc2.inputs[1].default_value=3.0; sc2.inputs[2].default_value=0.5; lk.new(si.outputs[0],sc2.inputs[0])
tr=nd.new('GeometryNodeTransform'); cmb=nd.new('ShaderNodeCombineXYZ')
lk.new(sc2.outputs[0],cmb.inputs['X']); lk.new(sc2.outputs[0],cmb.inputs['Y']); lk.new(sc2.outputs[0],cmb.inputs['Z'])
lk.new(ico.outputs['Mesh'],tr.inputs['Geometry']); lk.new(cmb.outputs[0],tr.inputs['Scale'])
setm=nd.new('GeometryNodeSetMaterial'); lk.new(tr.outputs[0],setm.inputs['Geometry'])
cmat=bpy.data.materials.new("core_m"); cmat.use_nodes=True; ct=cmat.node_tree; ct.nodes.clear()
co=ct.nodes.new('ShaderNodeOutputMaterial'); ce=ct.nodes.new('ShaderNodeEmission'); ce.inputs['Color'].default_value=(1.0,0.5,0.05,1); ce.inputs['Strength'].default_value=8.0
ct.links.new(ce.outputs['Emission'],co.inputs['Surface']); setm.inputs['Material'].default_value=cmat
lk.new(setm.outputs[0],gout.inputs[0])
core=bpy.data.objects.new("viz_core",bpy.data.meshes.new("viz_core")); coll.objects.link(core); core.modifiers.new("gn",'NODES').node_group=ng2

cam_d=bpy.data.cameras.new("viz_cam"); cam=bpy.data.objects.new("viz_cam",cam_d); coll.objects.link(cam)
cam.location=(0,-17,12); cam.rotation_euler=(math.radians(57),0,0); bpy.context.scene.camera=cam
sun_d=bpy.data.lights.new("viz_sun",'SUN'); sun_d.energy=1.2; sun=bpy.data.objects.new("viz_sun",sun_d); coll.objects.link(sun); sun.rotation_euler=(math.radians(50),0,0.6)
result={"ok":1}
''' % (0.010667,)

print("A:", send(stage_a))
print("B:", send(stage_b))

# render: beat frames vs between (beats ~0.76,1.26,1.76 -> f23,38,53; between 1.0,1.5 -> f30,45)
def rndr(fr, path):
    return send(r'''
import bpy
sc=bpy.context.scene; sc.frame_set(%d); sc.render.filepath="%s"; sc.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True); result={"f":%d}
''' % (fr, path, fr))

for fr, p in [(23,"/tmp/v2_beat_f23.png"),(30,"/tmp/v2_between_f30.png"),(38,"/tmp/v2_beat_f38.png"),(45,"/tmp/v2_between_f45.png")]:
    print("render", fr, send(r'''
import bpy
sc=bpy.context.scene; sc.frame_set(%d); sc.render.filepath="%s"; sc.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True); result={"f":%d}''' % (fr,p,fr)))
print("DONE")
