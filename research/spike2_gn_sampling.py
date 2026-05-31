"""Spike 2: GN time-sampling (most B). Throwaway — weryfikuje czy drzewo GN
czyta atrybut po czasie (Seconds/dt -> Sample Index) z poprawnym time->index.
Run: blender --background --python spike2_gn_sampling.py -- <analysis.json> [fps]
Czyta wartosc z powrotem przez depsgraph (probe vertex Z = sampled bass).
"""
import bpy, json, sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
analysis_path = argv[0]
fps = int(argv[1]) if len(argv) > 1 else 30

d = json.load(open(analysis_path))
fb = d["frequency_bands"]
times = np.array(fb["times"], dtype=np.float64)
dt = float(times[1] - times[0])
bass = np.array(fb["bass_energy"], dtype=np.float64)
p99 = float(np.percentile(bass, 99))
bass_n = (np.clip(bass / p99, 0, 1) if p99 > 0 else np.zeros_like(bass)).astype(np.float32)
N = len(bass_n)
sr = d["sample_rate"]
print(f"SPIKE2: sr={sr} dt={dt:.6f} N={N} fps={fps}")

# --- clean scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = fps

# --- 1) data object: mesh N verts, X=arange*dt, float attr bass_n ---
mesh = bpy.data.meshes.new("audio_data")
mesh.vertices.add(N)
co = np.zeros(N * 3, dtype=np.float32)
co[0::3] = np.arange(N, dtype=np.float32) * dt
mesh.vertices.foreach_set("co", co)
attr = mesh.attributes.new(name="bass_n", type='FLOAT', domain='POINT')
attr.data.foreach_set("value", bass_n)
mesh.update()
data_obj = bpy.data.objects.new("audio_data", mesh)
scene.collection.objects.link(data_obj)

# --- 2) probe: single vertex, GN sets its Z = sampled bass at scene time ---
pmesh = bpy.data.meshes.new("probe")
pmesh.vertices.add(1)
pmesh.vertices.foreach_set("co", [0.0, 0.0, 0.0])
pmesh.update()
probe = bpy.data.objects.new("probe", pmesh)
scene.collection.objects.link(probe)

# --- 3) GN node group (4.0+ interface API) ---
ng = bpy.data.node_groups.new("sampler", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
nodes, links = ng.nodes, ng.links
n_in = nodes.new('NodeGroupInput')
n_out = nodes.new('NodeGroupOutput')

st = nodes.new('GeometryNodeInputSceneTime')            # Seconds
div = nodes.new('ShaderNodeMath'); div.operation = 'DIVIDE'
links.new(st.outputs['Seconds'], div.inputs[0])
div.inputs[1].default_value = dt                         # index_f = Seconds / dt

floor = nodes.new('ShaderNodeMath'); floor.operation = 'FLOOR'
links.new(div.outputs[0], floor.inputs[0])
fr = nodes.new('ShaderNodeMath'); fr.operation = 'SUBTRACT'
links.new(div.outputs[0], fr.inputs[0]); links.new(floor.outputs[0], fr.inputs[1])
i1 = nodes.new('ShaderNodeMath'); i1.operation = 'ADD'; i1.inputs[1].default_value = 1.0
links.new(floor.outputs[0], i1.inputs[0])

obj_info = nodes.new('GeometryNodeObjectInfo')
obj_info.inputs['Object'].default_value = data_obj
obj_info.transform_space = 'ORIGINAL'

na = nodes.new('GeometryNodeInputNamedAttribute'); na.data_type = 'FLOAT'
na.inputs['Name'].default_value = "bass_n"

si0 = nodes.new('GeometryNodeSampleIndex'); si0.data_type = 'FLOAT'; si0.domain = 'POINT'; si0.clamp = True
si1 = nodes.new('GeometryNodeSampleIndex'); si1.data_type = 'FLOAT'; si1.domain = 'POINT'; si1.clamp = True
for si, idx in ((si0, floor), (si1, i1)):
    links.new(obj_info.outputs['Geometry'], si.inputs['Geometry'])
    links.new(na.outputs['Attribute'], si.inputs['Value'])
    links.new(idx.outputs[0], si.inputs['Index'])

# mix: v = v0*(1-frac) + v1*frac
mix = nodes.new('ShaderNodeMix'); mix.data_type = 'FLOAT'
links.new(fr.outputs[0], mix.inputs['Factor'])
links.new(si0.outputs[0], mix.inputs[2])   # A
links.new(si1.outputs[0], mix.inputs[3])   # B

# set position offset Z = mixed value
setpos = nodes.new('GeometryNodeSetPosition')
combine = nodes.new('ShaderNodeCombineXYZ')
links.new(mix.outputs[0], combine.inputs['Z'])
links.new(n_in.outputs[0], setpos.inputs['Geometry'])
links.new(combine.outputs[0], setpos.inputs['Offset'])
links.new(setpos.outputs[0], n_out.inputs[0])

modgn = probe.modifiers.new("gn", 'NODES'); modgn.node_group = ng

# --- 4) verify: for sampled frames, read probe evaluated Z vs expected ---
depsgraph = bpy.context.evaluated_depsgraph_get()
def sampled_z(frame):
    scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = probe.evaluated_get(dg)
    return float(ev.data.vertices[0].co.z)

def expected(frame):
    sec = frame / fps
    idx_f = sec / dt
    i0 = int(np.floor(idx_f)); i1 = i0 + 1; f = idx_f - i0
    i0c = min(max(i0, 0), N - 1); i1c = min(max(i1, 0), N - 1)
    return bass_n[i0c] * (1 - f) + bass_n[i1c] * f

print(f"{'frame':>6} {'sec':>7} {'GN_z':>10} {'expected':>10} {'abs_err':>10}")
max_err = 0.0
test_frames = [1, 30, 90, 150, 300, 600, 1200, 2000, int(d['duration']*fps)-1]
for fr_n in test_frames:
    gz = sampled_z(fr_n); ex = expected(fr_n); err = abs(gz - ex)
    max_err = max(max_err, err)
    print(f"{fr_n:>6} {fr_n/fps:>7.2f} {gz:>10.5f} {ex:>10.5f} {err:>10.2e}")
print(f"SPIKE2_RESULT sr={sr} max_abs_err={max_err:.3e} verdict={'PASS' if max_err < 1e-4 else 'FAIL'}")
