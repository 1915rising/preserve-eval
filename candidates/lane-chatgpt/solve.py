#!/usr/bin/env python3

import os
import sys
import math
import shutil
from collections import defaultdict


def parse_obj(path):
    vertices = []
    faces = []
    edge_indices = {}
    edge_faces = defaultdict(list)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue

            parts = line.split()
            kind = parts[0]

            if kind == "v" and len(parts) >= 4:
                try:
                    vertices.append(tuple(float(x) for x in parts[1:4]))
                except ValueError:
                    continue
            elif kind == "f" and len(parts) >= 4:
                face = []

                for token in parts[1:]:
                    try:
                        raw_index = int(token.split("/", 1)[0])
                    except (ValueError, IndexError):
                        face = []
                        break

                    if raw_index == 0:
                        face = []
                        break

                    if raw_index < 0:
                        index = len(vertices) + raw_index + 1
                    else:
                        index = raw_index

                    if index < 1 or index > len(vertices):
                        face = []
                        break

                    face.append(index)

                if len(face) < 3:
                    continue

                face_id = len(faces)
                faces.append(face)

                for i in range(len(face)):
                    a = face[i]
                    b = face[(i + 1) % len(face)]
                    edge = (min(a, b), max(a, b))

                    if edge not in edge_indices:
                        edge_indices[edge] = len(edge_indices)
                    edge_id = edge_indices[edge]
                    edge_faces[edge_id].append(face_id)

    return vertices, faces, edge_indices, edge_faces


def face_normal(vertices, face):
    """
    Calculate a polygon normal using Newell's method.
    Supports triangles, quads, and larger polygons.
    """
    nx = 0.0
    ny = 0.0
    nz = 0.0

    count = len(face)

    for i in range(count):
        p = vertices[face[i] - 1]
        q = vertices[face[(i + 1) % count] - 1]

        nx += (p[1] - q[1]) * (p[2] + q[2])
        ny += (p[2] - q[2]) * (p[0] + q[0])
        nz += (p[0] - q[0]) * (p[1] + q[1])

    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-15:
        return None
    return (nx / length, ny / length, nz / length)


def angle_between(a, b):
    dot = (
        a[0] * b[0]
        + a[1] * b[1]
        + a[2] * b[2]
    )
    dot = max(-1.0, min(1.0, dot))
    return math.acos(dot)


def calculate_seams(vertices, faces, edge_indices, edge_faces):
    """
    Mark boundary edges and geometrically sharp edges.
    If fewer than three seams are identified, add deterministic
    fallback edges selected using curvature and spatial distribution.
    """
    if not edge_indices:
        return []

    normals = [
        face_normal(vertices, face)
        for face in faces
    ]

    seam_indices = set()
    edge_scores = {}
    sharp_threshold = math.radians(30.0)

    for edge, edge_id in edge_indices.items():
        adjacent = edge_faces.get(edge_id, [])

        valid_normals = [
            normals[fid]
            for fid in adjacent
            if normals[fid] is not None
        ]

        # Boundary edges are useful seams, especially on open meshes.
        if len(adjacent) == 1:
            seam_indices.add(edge_id)
            edge_scores[edge_id] = math.pi
            continue

        # Calculate maximum dihedral angle for manifold and
        # non-manifold edges.
        maximum_angle = 0.0

        for i in range(len(valid_normals)):
            for j in range(i + 1, len(valid_normals)):
                angle = angle_between(
                    valid_normals[i],
                    valid_normals[j]
                )
                maximum_angle = max(maximum_angle, angle)

        edge_scores[edge_id] = maximum_angle

        if maximum_angle >= sharp_threshold:
            seam_indices.add(edge_id)

    total_edges = len(edge_indices)

    # Ensure at least three unique seams whenever three edges exist.
    target = min(3, total_edges)

    if len(seam_indices) < target:
        remaining = target - len(seam_indices)

        # Prefer edges with the highest dihedral angle.
        candidates = [
            edge_id
            for edge_id in range(total_edges)
            if edge_id not in seam_indices
        ]

        candidates.sort(
            key=lambda edge_id: (
                -edge_scores.get(edge_id, 0.0),
                edge_id
            )
        )

        for edge_id in candidates[:remaining]:
            seam_indices.add(edge_id)

        # Additional fallback: distribute selected seams across the
        # edge-index range if necessary.
        if len(seam_indices) < target:
            for i in range(total_edges):
                if i not in seam_indices:
                    seam_indices.add(i)

                if len(seam_indices) >= target:
                    break

    return sorted(seam_indices)


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python3 solve.py base.obj out_dir",
            file=sys.stderr
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isfile(input_path):
        print("Input OBJ file does not exist.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Parse geometry exclusively for seam selection.
    vertices, faces, edge_indices, edge_faces = parse_obj(input_path)

    seams = calculate_seams(
        vertices,
        faces,
        edge_indices,
        edge_faces
    )

    # Preserve the original OBJ byte-for-byte.
    output_obj = os.path.join(output_dir, "after.obj")
    shutil.copyfile(input_path, output_obj)

    # Store seam indices separately.
    output_seams = os.path.join(output_dir, "after.seams")
    with open(output_seams, "w", encoding="ascii", newline="\n") as f:
        for edge_id in seams:
            f.write(str(edge_id) + "\n")


if __name__ == "__main__":
    main()
