"""Minimalny wizualizer (Spike 0 artefakt) — napedza ZYWY Blender przez socket.
Buduje: data-object (5 atrybutow z realnej analizy jazz), GN scrolling-bars ring
sterowany pasmami, srodek pulsujacy na beat_env. Screenshoty do /tmp.
Run: python3 research/build_visualizer_v1.py
"""
import json, socket, sys, time

HOST, PORT = "localhost", 9876

def send(code, strict_json=False, timeout=120):
    req = json.dumps({"type": "execute", "code": code, "strict_json": strict_json}) + "\0"
    with socket.socket() as s:
        s.settimeout(timeout); s.connect((HOST, PORT)); s.sendall(req.encode())
        buf = bytearray()
        while True:
            c = s.recv(65536)
            if not c: break
            buf.extend(c)
            if b"\0" in buf: break
    resp = json.loads(bytes(buf).partition(b"\0")[0].decode())
    if resp.get("status") != "ok":
        print("  !! ERROR:", json.dumps(resp, indent=2)[:1200]); sys.exit(1)
    return resp.get("result")

ANALYSIS = "/Users/wokoziej/dev/setka-monorepo/research/audio/analysis/jazz_120s_48k_analysis.json"

# ---------------- STAGE A: scene + data prep + data-object ----------------
stage_a = r'''
import bpy, json, numpy as np

ANALYSIS = "%s"
FPS = 30
d = json.load(open(ANALYSIS))
fb = d["frequency_bands"]; ae = d["animation_events"]
times = np.array(fb["times"], float); dt = float(times[1]-times[0]); N = len(times)
def norm(a):
    a = np.array(a, float); p = np.percentile(a, 99)
    return (np.clip(a/p, 0, 1) if p > 0 else np.zeros_like(a)).astype(np.float32)
bass_n, mid_n, high_n = norm(fb["bass_energy"]), norm(fb["mid_energy"]), norm(fb["high_energy"])
# decay envelopes for beats / peaks (precomputed, approach C)
def env(events, decay=0.18):
    e = np.zeros(N, np.float32)
    for t in events:
        i = int(round(t/dt))
        for k in range(0, int(decay/dt)+1):
            j = i+k
            if 0 <= j < N: e[j] = max(e[j], 1.0 - k*dt/decay)
    return e
beat_env = env(ae.get("beats", [])); peak_env = env(ae.get("energy_peaks", []), 0.25)

# dedicated collection (nie ruszamy reszty)
for c in list(bpy.data.collections):
    if c.name == "cymatic_viz":
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
coll = bpy.data.collections.new("cymatic_viz"); bpy.context.scene.collection.children.link(coll)

# data-object: N verts, X=time, 5 float attrs
me = bpy.data.meshes.new("audio_data"); me.vertices.add(N)
co = np.zeros(N*3, np.float32); co[0::3] = np.arange(N, dtype=np.float32)*dt
me.vertices.foreach_set("co", co)
for name, arr in [("bass_n",bass_n),("mid_n",mid_n),("high_n",high_n),("beat_env",beat_env),("peak_env",peak_env)]:
    a = me.attributes.new(name=name, type='FLOAT', domain='POINT'); a.data.foreach_set("value", arr)
me.update()
obj = bpy.data.objects.new("audio_data", me); coll.objects.link(obj); obj.hide_render = True; obj.hide_viewport = True

# scene/render
sc = bpy.context.scene; sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = int(d["duration"]*FPS)
sc.render.resolution_x = 1280; sc.render.resolution_y = 720
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'
# dark world
w = bpy.data.worlds.get("cymatic_world") or bpy.data.worlds.new("cymatic_world")
w.use_nodes = True; bg = w.node_tree.nodes.get("Background")
if bg: bg.inputs[0].default_value = (0.01,0.01,0.02,1); bg.inputs[1].default_value = 0.3
sc.world = w
result = {"N": N, "dt": round(dt,6), "frame_end": sc.frame_end,
          "bass_max": float(bass_n.max()), "beats": len(ae.get("beats",[])), "engine": sc.render.engine}
''' % ANALYSIS

print("STAGE A: scene + data-object ...")
print(" ", send(stage_a))

# ---------------- STAGE B: GN ring of bars + material + camera + light ----------------
stage_b = r'''
import bpy, math
from mathutils import Vector
coll = bpy.data.collections["cymatic_viz"]
audio = bpy.data.objects["audio_data"]
DT = %f
M = 128            # liczba slupkow w pierscieniu
STRIDE = 0.045     # offset czasu na slupek -> okno historii ~5.8s
RAD = 5.0

def ring(name, attr_name, radius, zcol):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nd, lk = ng.nodes, ng.links
    gin = nd.new('NodeGroupInput'); gout = nd.new('NodeGroupOutput')
    circ = nd.new('GeometryNodeMeshCircle'); circ.fill_type='NONE'; circ.inputs['Vertices'].default_value=M; circ.inputs['Radius'].default_value=radius
    cube = nd.new('GeometryNodeMeshCube'); cube.inputs['Size'].default_value=(0.18,0.18,1.0)
    iop = nd.new('GeometryNodeInstanceOnPoints')
    lk.new(circ.outputs['Mesh'], iop.inputs['Points']); lk.new(cube.outputs['Mesh'], iop.inputs['Instance'])
    # h-field: sample band at (SceneTime - index*STRIDE)
    idx = nd.new('GeometryNodeInputIndex')
    st = nd.new('GeometryNodeInputSceneTime')
    offs = nd.new('ShaderNodeMath'); offs.operation='MULTIPLY'; offs.inputs[1].default_value=STRIDE
    lk.new(idx.outputs['Index'], offs.inputs[0])
    tsec = nd.new('ShaderNodeMath'); tsec.operation='SUBTRACT'
    lk.new(st.outputs['Seconds'], tsec.inputs[0]); lk.new(offs.outputs[0], tsec.inputs[1])
    sidx = nd.new('ShaderNodeMath'); sidx.operation='DIVIDE'; sidx.inputs[1].default_value=DT
    lk.new(tsec.outputs[0], sidx.inputs[0])
    flo = nd.new('ShaderNodeMath'); flo.operation='FLOOR'; lk.new(sidx.outputs[0], flo.inputs[0])
    oinfo = nd.new('GeometryNodeObjectInfo'); oinfo.inputs['Object'].default_value=audio; oinfo.transform_space='ORIGINAL'
    na = nd.new('GeometryNodeInputNamedAttribute'); na.data_type='FLOAT'; na.inputs['Name'].default_value=attr_name
    si = nd.new('GeometryNodeSampleIndex'); si.data_type='FLOAT'; si.domain='POINT'; si.clamp=True
    lk.new(oinfo.outputs['Geometry'], si.inputs['Geometry']); lk.new(na.outputs['Attribute'], si.inputs['Value']); lk.new(flo.outputs[0], si.inputs['Index'])
    # scale Z = 0.1 + h*6
    hsc = nd.new('ShaderNodeMath'); hsc.operation='MULTIPLY_ADD'; hsc.inputs[1].default_value=6.0; hsc.inputs[2].default_value=0.1
    lk.new(si.outputs[0], hsc.inputs[0])
    comb = nd.new('ShaderNodeCombineXYZ'); comb.inputs['X'].default_value=1; comb.inputs['Y'].default_value=1
    lk.new(hsc.outputs[0], comb.inputs['Z'])
    scl = nd.new('GeometryNodeScaleInstances')
    lk.new(iop.outputs['Instances'], scl.inputs['Instances']); lk.new(comb.outputs[0], scl.inputs['Scale'])
    setm = nd.new('GeometryNodeSetMaterial')
    lk.new(scl.outputs[0], setm.inputs['Geometry'])
    # material: emission, color by world Z
    mat = bpy.data.materials.new(name+"_mat"); mat.use_nodes=True
    mt=mat.node_tree; mt.nodes.clear()
    out=mt.nodes.new('ShaderNodeOutputMaterial'); em=mt.nodes.new('ShaderNodeEmission')
    geo=mt.nodes.new('ShaderNodeNewGeometry'); sep=mt.nodes.new('ShaderNodeSeparateXYZ')
    mr=mt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value=0; mr.inputs['From Max'].default_value=6
    ramp=mt.nodes.new('ShaderNodeValToRGB')
    e=ramp.color_ramp.elements; e[0].position=0.0; e[0].color=zcol[0]; e[1].position=1.0; e[1].color=zcol[1]
    mt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    mt.links.new(sep.outputs['Z'], mr.inputs['Value']); mt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    mt.links.new(ramp.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value=4.0
    mt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    setm.inputs['Material'].default_value=mat
    lk.new(setm.outputs['Geometry'], gout.inputs[0])
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name)); coll.objects.link(o)
    m = o.modifiers.new("gn",'NODES'); m.node_group=ng
    return o

ring("viz_bass","bass_n",RAD,        [(0.0,0.2,1.0,1),(0.2,0.9,1.0,1)])
ring("viz_mid","mid_n",  RAD+1.4,    [(0.0,1.0,0.4,1),(1.0,1.0,0.2,1)])
ring("viz_high","high_n",RAD+2.8,    [(1.0,0.3,0.6,1),(1.0,0.9,0.9,1)])

# center sphere pulsing on beat_env (own GN)
ng2 = bpy.data.node_groups.new("viz_core_gn",'GeometryNodeTree')
ng2.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
ng2.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
nd,lk=ng2.nodes,ng2.links
gin=nd.new('NodeGroupInput'); gout=nd.new('NodeGroupOutput')
ico=nd.new('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value=1.0; ico.inputs['Subdivisions'].default_value=3
st=nd.new('GeometryNodeInputSceneTime')
sidx=nd.new('ShaderNodeMath'); sidx.operation='DIVIDE'; sidx.inputs[1].default_value=DT; lk.new(st.outputs['Seconds'],sidx.inputs[0])
flo=nd.new('ShaderNodeMath'); flo.operation='FLOOR'; lk.new(sidx.outputs[0],flo.inputs[0])
oinfo=nd.new('GeometryNodeObjectInfo'); oinfo.inputs['Object'].default_value=audio; oinfo.transform_space='ORIGINAL'
na=nd.new('GeometryNodeInputNamedAttribute'); na.data_type='FLOAT'; na.inputs['Name'].default_value="beat_env"
si=nd.new('GeometryNodeSampleIndex'); si.data_type='FLOAT'; si.domain='POINT'; si.clamp=True
lk.new(oinfo.outputs['Geometry'],si.inputs['Geometry']); lk.new(na.outputs['Attribute'],si.inputs['Value']); lk.new(flo.outputs[0],si.inputs['Index'])
sc=nd.new('ShaderNodeMath'); sc.operation='MULTIPLY_ADD'; sc.inputs[1].default_value=1.6; sc.inputs[2].default_value=0.8; lk.new(si.outputs[0],sc.inputs[0])
tr=nd.new('GeometryNodeTransform');
# scale via Combine
cmb=nd.new('ShaderNodeCombineXYZ'); lk.new(sc.outputs[0],cmb.inputs['X']); lk.new(sc.outputs[0],cmb.inputs['Y']); lk.new(sc.outputs[0],cmb.inputs['Z'])
lk.new(ico.outputs['Mesh'],tr.inputs['Geometry']); lk.new(cmb.outputs[0],tr.inputs['Scale'])
setm=nd.new('GeometryNodeSetMaterial'); lk.new(tr.outputs[0],setm.inputs['Geometry'])
cmat=bpy.data.materials.new("core_mat"); cmat.use_nodes=True; ct=cmat.node_tree; ct.nodes.clear()
co=ct.nodes.new('ShaderNodeOutputMaterial'); ce=ct.nodes.new('ShaderNodeEmission'); ce.inputs['Color'].default_value=(1.0,0.6,0.1,1); ce.inputs['Strength'].default_value=6.0
ct.links.new(ce.outputs['Emission'],co.inputs['Surface']); setm.inputs['Material'].default_value=cmat
lk.new(setm.outputs[0],gout.inputs[0])
core=bpy.data.objects.new("viz_core", bpy.data.meshes.new("viz_core")); coll.objects.link(core)
core.modifiers.new("gn",'NODES').node_group=ng2

# camera + sun
cam_d=bpy.data.cameras.new("viz_cam"); cam=bpy.data.objects.new("viz_cam",cam_d); coll.objects.link(cam)
cam.location=(0,-16,11); cam.rotation_euler=(math.radians(58),0,0)
bpy.context.scene.camera=cam
sun_d=bpy.data.lights.new("viz_sun",'SUN'); sun_d.energy=1.5; sun=bpy.data.objects.new("viz_sun",sun_d); coll.objects.link(sun); sun.rotation_euler=(math.radians(50),0,0.6)
result = {"rings":3, "core":True, "cam":"viz_cam"}
''' % (0.010667, )

print("STAGE B: GN rings + core + camera/light ...")
print(" ", send(stage_b))

# ---------------- STAGE C: render 3 frames (rozne momenty energii) ----------------
def render_frame(fr, path):
    code = r'''
import bpy
sc=bpy.context.scene; sc.frame_set(%d)
sc.render.filepath="%s"; sc.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
result={"frame":%d,"path":"%s"}
''' % (fr, path, fr, path)
    return send(code, timeout=180)

frames = {30:"/tmp/viz_f030.png", 90:"/tmp/viz_f090.png", 600:"/tmp/viz_f600.png"}
print("STAGE C: render klatek ...")
for fr, p in frames.items():
    print(" ", render_frame(fr, p))
print("DONE")

