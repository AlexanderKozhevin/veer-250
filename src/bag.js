import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const v = (x, y, z) => new THREE.Vector3(x, y, z);
const mix = THREE.MathUtils.lerp;
const smooth = THREE.MathUtils.smoothstep;
const clamp = THREE.MathUtils.clamp;
const pieces = [];
const moving = [];
const hideColor = new THREE.Color();
const dark = new THREE.Color('#210812'),
  cherry = new THREE.Color('#590d26'),
  high = new THREE.Color('#711a35');

function grain() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const ctx = c.getContext('2d'),
    im = ctx.createImageData(256, 256);
  let seed = 67341;
  for (let i = 0; i < im.data.length; i += 4) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const value = 109 + (seed >>> 26) * 0.6;
    im.data[i] = im.data[i + 1] = im.data[i + 2] = value;
    im.data[i + 3] = 255;
  }
  ctx.putImageData(im, 0, 0);
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
}
const leather = new THREE.MeshPhysicalMaterial({
  color: 0xffffff,
  vertexColors: true,
  roughness: 0.36,
  clearcoat: 0.35,
  clearcoatRoughness: 0.3,
  metalness: 0,
  side: THREE.DoubleSide,
  envMapIntensity: 0.88,
});
const suede = new THREE.MeshStandardMaterial({
  color: 0x775346,
  roughness: 0.94,
  side: THREE.DoubleSide,
});
const lining = new THREE.MeshStandardMaterial({
  color: 0x583136,
  roughness: 0.78,
  side: THREE.DoubleSide,
});
const edging = new THREE.MeshStandardMaterial({
  color: 0x340e1b,
  roughness: 0.45,
  side: THREE.DoubleSide,
});
const thread = new THREE.MeshStandardMaterial({ color: 0xbc8580, roughness: 0.77 });
const gold = new THREE.MeshStandardMaterial({ color: 0xd3a45e, metalness: 0.82, roughness: 0.23 });
const insert = new THREE.MeshStandardMaterial({
  color: 0x8c7056,
  roughness: 0.98,
  side: THREE.DoubleSide,
});
const stitchGeom = new THREE.SphereGeometry(1, 6, 4);
const yAxis = v(0, 1, 0);
const hardwareMatrix = new THREE.Object3D();

function tint(y, u, t) {
  hideColor
    .copy(dark)
    .lerp(cherry, 0.12 + 0.8 * smooth(y, 5, 169))
    .lerp(high, 0.08 + 0.09 * Math.sin(u * Math.PI) * Math.sin(t * Math.PI));
  return hideColor;
}
function piece(root, name, direction) {
  const group = new THREE.Group();
  group.name = name;
  root.add(group);
  pieces.push({ group, direction });
  return group;
}
function grid(group, nu, nv, sample, mat, vertexTint = false, updateable = false) {
  const count = (nu + 1) * (nv + 1),
    pos = new Float32Array(count * 3),
    uv = new Float32Array(count * 2),
    colors = new Float32Array(count * 3);
  const tri = [];
  for (let j = 0; j < nv; j++)
    for (let i = 0; i < nu; i++) {
      const a = j * (nu + 1) + i,
        b = a + 1,
        c = a + nu + 1,
        d = c + 1;
      tri.push(a, b, c, b, d, c);
    }
  const geom = new THREE.BufferGeometry();
  geom.setIndex(tri);
  geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geom.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  if (vertexTint) geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  const update = () => {
    for (let j = 0; j <= nv; j++)
      for (let i = 0; i <= nu; i++) {
        const u = i / nu,
          t = j / nv,
          k = j * (nu + 1) + i,
          p = sample(u, t);
        pos[k * 3] = p.x;
        pos[k * 3 + 1] = p.y;
        pos[k * 3 + 2] = p.z;
        uv[k * 2] = u * 2.1;
        uv[k * 2 + 1] = t * 3.6;
        if (vertexTint) {
          const color = typeof vertexTint === 'function' ? vertexTint(p.y, u, t) : tint(p.y, u, t);
          color.toArray(colors, k * 3);
        }
      }
    geom.attributes.position.needsUpdate = true;
    if (vertexTint) geom.attributes.color.needsUpdate = true;
    geom.computeVertexNormals();
    geom.computeBoundingSphere();
  };
  update();
  if (updateable) moving.push(update);
  const mesh = new THREE.Mesh(geom, mat);
  group.add(mesh);
  return mesh;
}
function pipe(group, points, radius, material) {
  const filtered = points.filter((p, i) => i === 0 || p.distanceToSquared(points[i - 1]) > 1e-7);
  if (filtered.length < 2) return;
  const curve = new THREE.CatmullRomCurve3(filtered, false, 'centripetal');
  group.add(
    new THREE.Mesh(
      new THREE.TubeGeometry(curve, Math.max(6, filtered.length * 2), radius, 6, false),
      material,
    ),
  );
}
function stitches(group, lines, r = 0.39, updateable = false) {
  const pairs = [];
  for (const { points, fn } of lines) {
    let len = 0;
    const cumulative = [0];
    for (let i = 1; i < points.length; i++) {
      len += new THREE.Vector2(...points[i]).distanceTo(new THREE.Vector2(...points[i - 1]));
      cumulative.push(len);
    }
    const n = Math.max(1, Math.round(len / 4));
    const at = (s) => {
      let i = 1;
      while (i < cumulative.length - 1 && cumulative[i] < s) i++;
      const t = (s - cumulative[i - 1]) / (cumulative[i] - cumulative[i - 1] || 1);
      return [mix(points[i - 1][0], points[i][0], t), mix(points[i - 1][1], points[i][1], t)];
    };
    for (let i = 0; i < n; i++)
      pairs.push([at(((i + 0.13) * len) / n), at(((i + 0.84) * len) / n), fn]);
  }
  const mesh = new THREE.InstancedMesh(stitchGeom, thread, pairs.length);
  const update = () => {
    pairs.forEach(([a, b, fn], i) => {
      const p = fn(...a),
        q = fn(...b),
        dir = q.clone().sub(p);
      hardwareMatrix.position.copy(p).lerp(q, 0.5);
      hardwareMatrix.quaternion.setFromUnitVectors(yAxis, dir.clone().normalize());
      hardwareMatrix.scale.set(r, dir.length() * 0.5, r * 0.78);
      hardwareMatrix.updateMatrix();
      mesh.setMatrixAt(i, hardwareMatrix.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
    mesh.computeBoundingSphere();
  };
  update();
  if (updateable) moving.push(update);
  group.add(mesh);
}
function polyMesh(group, outline, transform, material, thickness, bevel = 0.28) {
  const shape = new THREE.Shape(outline.map(([x, y]) => new THREE.Vector2(x, -y)));
  const geom = new THREE.ExtrudeGeometry(shape, {
    depth: thickness,
    bevelEnabled: bevel > 0,
    bevelSize: bevel,
    bevelThickness: bevel,
    bevelSegments: 2,
    curveSegments: 4,
  });
  const p = geom.attributes.position,
    colors = new Float32Array(p.count * 3),
    q = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    q.fromBufferAttribute(p, i);
    const w = transform(q.x, -q.y, q.z);
    p.setXYZ(i, w.x, w.y, w.z);
    tint(w.y, 0.5, 0.5).toArray(colors, 3 * i);
  }
  if (material.vertexColors) geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geom.computeVertexNormals();
  group.add(new THREE.Mesh(geom, material));
}
const samples = (n, fn) => Array.from({ length: n + 1 }, (_, i) => fn(i / n));

export function buildBag(root, data) {
  const texture = grain();
  leather.bumpMap = texture;
  leather.bumpScale = 0.22;
  // Each body panel uses exactly the same four boundary vertices as the flat development.
  const keys = ['C', 'B', 'A', 'B', 'C'];
  [1, -1].forEach((side) => {
    keys.forEach((key, i) => {
      const world = (p) => v(p[0], p[1], p[2] * side);
      const b0 = world(data.bottom[i]),
        b1 = world(data.bottom[i + 1]),
        t0 = world(data.top[i]),
        t1 = world(data.top[i + 1]);
      const du = b1.clone().sub(b0),
        dv = t0.clone().sub(b0);
      const normal = du.clone().cross(dv).normalize().multiplyScalar(side);
      const group = piece(
        root,
        key,
        v((i - 2) * 28, 14 - Math.abs(i - 2) * 2, side * (51 - Math.abs(i - 2) * 7)),
      );
      const point = (u, t, layer = 0) => {
        const a = b0.clone().lerp(b1, u),
          b = t0.clone().lerp(t1, u);
        const fullness = key === 'A' ? 3.0 + 3.5 * (1 - smooth(t, 0.45, 0.78)) : 4.8;
        const bulge = fullness * Math.sin(Math.PI * u) * Math.sin(Math.PI * t);
        return a.lerp(b, t).addScaledVector(normal, bulge + layer);
      };
      // Keep front-facing normals outside on both mirrored halves.
      const outside = (u, t) => point(side === 1 ? u : 1 - u, t);
      const inside = (u, t) => point(side === 1 ? 1 - u : u, t, -1.45);
      grid(group, 15, 21, outside, leather, true);
      grid(group, 10, 14, inside, suede);
      pipe(
        group,
        samples(16, (u) => point(u, 1, -0.5)),
        0.86,
        edging,
      );
      for (const u of [0, 1])
        pipe(
          group,
          samples(16, (t) => point(u, t, -0.5)),
          0.63,
          edging,
        );
      const leftDist = b0.distanceTo(t0),
        rightDist = b1.distanceTo(t1),
        width = b0.distanceTo(b1);
      // One decorative row per vertical join, plus a row at the finished top edge.
      const lines = [
        {
          points: [
            [0, 0],
            [0, leftDist],
          ],
          fn: (_, s) => point(0.035, s / leftDist, 0.38),
        },
        {
          points: [
            [0, 0],
            [width, 0],
          ],
          fn: (x) => point(x / width, 0.985, 0.38),
        },
      ];
      if (i === 4)
        lines.push({
          points: [
            [0, 0],
            [0, rightDist],
          ],
          fn: (_, s) => point(0.963, s / rightDist, 0.38),
        });
      stitches(group, lines);
    });
  });
  const base = piece(root, 'D', v(0, -71, 0));
  for (let i = 0; i < 5; i++) {
    const [l, r] = [data.bottom[i], data.bottom[i + 1]];
    grid(
      base,
      1,
      1,
      (u, w) => v(mix(l[0], r[0], u), mix(l[1], r[1], u) - 0.25, mix(l[2], r[2], u) * (2 * w - 1)),
      leather,
      true,
    );
  }
  const support = piece(root, 'I', v(0, -34, 0));
  polyMesh(support, data.parts.I.cut, (x, d, z) => v(x, 0.3 + z, d), insert, 1.1);
  const backAt = (y) => -(68 - (37 * clamp(y, 0, 242)) / 242);
  const handleAt = (x, d, z) => {
    const y = 350 - d;
    return v(x, y, backAt(y) - 2.3 - 4.6 * smooth(y, 241, 318) - z);
  };
  for (let ply = 0; ply < 2; ply++) {
    const handle = piece(root, 'G', v(0, 76, ply === 0 ? -31 : -12));
    polyMesh(
      handle,
      data.parts.G.cut,
      (x, d, z) => handleAt(x, d, z + ply * 1.35),
      leather,
      1.35,
      0.22,
    );
    const lines = data.parts.G.marks
      .filter((m) => m.kind === 'stitch' || m.kind === 'rear')
      .map((m) => ({ points: m.p, fn: (x, d) => handleAt(x, d, ply ? 3.05 : -0.35) }));
    stitches(handle, lines, 0.32);
  }
  for (const side of [-1, 1]) {
    const patch = piece(root, 'H', v(side * 17, 31, side === 1 ? -50 : -46));
    polyMesh(
      patch,
      data.parts.H.cut,
      (x, d, z) => v(side * 52 + x, 222 - d, backAt(222 - d) + 2.5 + z),
      lining,
      1.2,
      0.1,
    );
  }
  // Rotate the successive tangents, integrating their lengths to keep the flexible flap inextensible.
  const profile = data.flap.map((row) => [...row]);
  const total = profile.at(-1)[0];
  let opened = 0;
  function updateProfile(a) {
    for (let i = 1; i < profile.length; i++) {
      const p = data.flap[i],
        last = data.flap[i - 1],
        s = (p[0] + last[0]) / 2;
      const dz = p[1] - last[1],
        dy = p[2] - last[2],
        ds = Math.hypot(dz, dy);
      const closedAngle = Math.atan2(dy, dz),
        openAngle = 0.99 + 0.32 * smooth(s, 45, total);
      const angle = mix(closedAngle, openAngle, a * smooth(s, 18, 78));
      profile[i][1] = profile[i - 1][1] + Math.cos(angle) * ds;
      profile[i][2] = profile[i - 1][2] + Math.sin(angle) * ds;
    }
  }
  const halfWidth = (s) => {
    if (s > total - 35) return 56 + 35 * Math.sqrt(Math.max(0, 1 - ((s - total + 35) / 35) ** 2));
    return 45 + 46 * smooth(s, 15, 70);
  };
  function section(s) {
    s = clamp(s, 0, total);
    let lo = 0,
      hi = profile.length - 1;
    while (hi - lo > 1) {
      const i = (hi + lo) >> 1;
      if (profile[i][0] <= s) lo = i;
      else hi = i;
    }
    const a = profile[lo],
      b = profile[hi],
      t = (s - a[0]) / (b[0] - a[0]);
    const dz = b[1] - a[1],
      dy = b[2] - a[2],
      length = Math.hypot(dz, dy);
    return [mix(a[1], b[1], t), mix(a[2], b[2], t), dz / length, -dy / length];
  }
  function flapAt(x, s, layer) {
    const [z, y, ny, nz] = section(s),
      w = halfWidth(s);
    const dome = 3.0 * Math.max(0, 1 - (x / w) ** 2) * Math.sin((Math.PI * s) / total);
    return v(x, y + ny * (layer + dome), z + nz * (layer + dome));
  }
  const outer = piece(root, 'E', v(0, 47, 97)),
    inner = piece(root, 'F', v(0, 30, 68));
  const flapTone = (_y, u, t) =>
    hideColor
      .copy(dark)
      .lerp(cherry, 0.2 + 0.77 * (1 - smooth(t, 0.54, 0.96)))
      .lerp(high, 0.09 + 0.12 * Math.sin(Math.PI * u));
  grid(
    outer,
    25,
    84,
    (u, t) => flapAt((1 - 2 * u) * halfWidth(t * total), t * total, 1.3),
    leather,
    flapTone,
    true,
  );
  grid(
    inner,
    22,
    72,
    (u, t) => flapAt((2 * u - 1) * halfWidth(t * total), t * total, -0.7),
    lining,
    false,
    true,
  );
  for (const side of [-1, 1]) {
    grid(
      outer,
      1,
      84,
      (u, t) => flapAt(side * halfWidth(t * total), t * total, 1.3 * (1 - u)),
      edging,
      false,
      true,
    );
    grid(
      inner,
      1,
      84,
      (u, t) => flapAt(side * halfWidth(t * total), t * total, -0.7 * u),
      edging,
      false,
      true,
    );
  }
  for (const s of [0, total])
    grid(
      outer,
      25,
      1,
      (u, t) => flapAt((2 * u - 1) * halfWidth(s), s, 1.3 - 2 * t),
      edging,
      false,
      true,
    );
  const st = data.parts.E.marks.find((m) => m.kind === 'stitch');
  stitches(outer, [{ points: st.p, fn: (x, s) => flapAt(x, s, 1.7) }], 0.4, true);
  const bar = new THREE.Mesh(new RoundedBoxGeometry(50, 9.5, 3.6, 3, 1.65), gold);
  outer.add(bar);
  const male = new THREE.Mesh(new THREE.CylinderGeometry(7, 7, 2.8, 32), gold);
  inner.add(male);
  moving.push(() => {
    const s = total - 4.4;
    bar.position.copy(flapAt(0, s, 2.15));
    const z = section(s);
    bar.rotation.x = Math.atan2(-z[2], z[3]);
    const snap = section(data.magnetS);
    male.position.copy(flapAt(0, data.magnetS, -1.65));
    male.quaternion.setFromUnitVectors(yAxis, v(0, snap[2], snap[3]).normalize());
  });
  const frontSnapY = section(data.magnetS)[1],
    faceZ = 68 - (37 * frontSnapY) / 242;
  const hardware = piece(root, 'Кнопка', v(0, 12, 56));
  const female = new THREE.Mesh(new THREE.CylinderGeometry(7, 7, 2, 36), gold);
  female.position.set(0, frontSnapY, faceZ + 2.4);
  female.rotation.x = Math.PI * 0.45;
  hardware.add(female);
  for (let i = 0; i < 2; i++) {
    const backing = piece(root, 'J', v(0, 14, 23 - 11 * i));
    polyMesh(
      backing,
      data.parts.J.cut,
      (x, d, z) => v(x, frontSnapY - d, 68 - (37 * (frontSnapY - d)) / 242 - 2 - i * 0.8 - z),
      lining,
      0.7,
      0.1,
    );
  }
  moving.forEach((f) => f());
  return (spread, open) => {
    pieces.forEach(({ group, direction }) => group.position.copy(direction).multiplyScalar(spread));
    if (Math.abs(open - opened) > 0.0008 || (open !== opened && (open === 0 || open === 1))) {
      updateProfile(open);
      moving.forEach((f) => f());
      opened = open;
    }
  };
}
