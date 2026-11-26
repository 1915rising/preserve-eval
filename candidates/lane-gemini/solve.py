import math
import os
import shutil
import sys


def parse_obj(filepath):
    vertices = []
    faces = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "v" and len(parts) >= 4:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif tag == "f" and len(parts) >= 4:
                face_verts = []
                for tok in parts[1:]:
                    v_str = tok.split("/")[0]
                    if v_str:
                        v_idx = int(v_str)
                        if v_idx < 0:
                            v_idx = len(vertices) + 1 + v_idx
                        face_verts.append(v_idx)
                if len(face_verts) >= 3:
                    faces.append(face_verts)
    return vertices, faces


def compute_face_normal(vertices, face):
    nx, ny, nz = 0.0, 0.0, 0.0
    n = len(face)
    for i in range(n):
        v1 = vertices[face[i] - 1]
        v2 = vertices[face[(i + 1) % n] - 1]
        nx += (v1[1] - v2[1]) * (v1[2] + v2[2])
        ny += (v1[2] - v2[2]) * (v1[0] + v2[0])
        nz += (v1[0] - v2[0]) * (v1[1] + v2[1])
    length = math.hypot(nx, ny, nz)
    if length < 1e-12:
        return None
    return (nx / length, ny / length, nz / length)


def build_edges_and_select_seams(vertices, faces):
    edge_to_idx = {}
    edge_faces = {}
    edge_lengths = {}

    for f_idx, face in enumerate(faces):
        normal = compute_face_normal(vertices, face)
        m = len(face)
        for i in range(m):
            u = face[i]
            v = face[(i + 1) % m]
            if u == v:
                continue
            key = (u, v) if u < v else (v, u)
            if key not in edge_to_idx:
                edge_to_idx[key] = len(edge_to_idx)
                edge_faces[key] = []
                p1 = vertices[key[0] - 1]
                p2 = vertices[key[1] - 1]
                edge_lengths[key] = math.dist(p1, p2)
            edge_faces[key].append((f_idx, normal))

    total_edges = len(edge_to_idx)
    if total_edges == 0:
        return []

    scored_edges = []
    for key, e_idx in edge_to_idx.items():
        adj = edge_faces[key]
        length = edge_lengths[key]
        if len(adj) == 1:
            # Boundary edge on open mesh: high priority seam
            score = 10.0 + length
        elif len(adj) >= 2:
            # Compute maximum dihedral angle among incident valid face normals
            valid_normals = [n for _, n in adj if n is not None]
            max_angle = 0.0
            for i in range(len(valid_normals)):
                for j in range(i + 1, len(valid_normals)):
                    n1 = valid_normals[i]
                    n2 = valid_normals[j]
                    dot = max(-1.0, min(1.0, n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2]))
                    angle = math.acos(dot)
                    if angle > max_angle:
                        max_angle = angle
            if len(adj) > 2:
                # Non-manifold edge
                score = 5.0 + max_angle
            else:
                score = max_angle
        else:
            score = 0.0
        scored_edges.append((score, length, e_idx))

    # Select sharp/boundary edges (dihedral angle > ~30 degrees = 0.5236 rad)
    sharp_threshold = math.radians(30.0)
    selected = [e_idx for score, _, e_idx in scored_edges if score > sharp_threshold]

    # Ensure at least 3 valid unique seams are marked (or all edges if mesh has < 3)
    min_seams = min(3, total_edges)
    if len(selected) < min_seams:
        selected_set = set(selected)
        # Sort remaining edges by highest dihedral angle, then longest edge length, then index
        ranked = sorted(scored_edges, key=lambda x: (-x[0], -x[1], x[2]))
        for _, _, e_idx in ranked:
            if e_idx not in selected_set:
                selected.append(e_idx)
                selected_set.add(e_idx)
                if len(selected) >= min_seams:
                    break

    return sorted(selected)


def main():
    if len(sys.argv) != 3:
        sys.exit(1)

    base_obj_path = sys.argv[1]
    out_dir = sys.argv[2]

    os.makedirs(out_dir, exist_ok=True)
    after_obj_path = os.path.join(out_dir, "after.obj")
    after_seams_path = os.path.join(out_dir, "after.seams")

    # Preserve exact geometry, vertices, UVs, and face ordering
    shutil.copyfile(base_obj_path, after_obj_path)

    vertices, faces = parse_obj(base_obj_path)
    seams = build_edges_and_select_seams(vertices, faces)

    with open(after_seams_path, "w", encoding="utf-8") as f:
        for edge_idx in seams:
            f.write(f"{edge_idx}\n")


if __name__ == "__main__":
    main()
