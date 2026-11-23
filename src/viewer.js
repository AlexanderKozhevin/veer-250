import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { buildBag } from './bag.js';

function environment(renderer) {
  // A panoramic light tent. Linear HDR texels retain the long reflections of softboxes on leather.
  const w = 256,
    h = 128,
    values = new Float32Array(w * h * 4);
  const boxes = [
    [-0.72, 0.35, 0.58, 0.4, 0.73, 3.7, [1, 0.91, 0.85]],
    [-0.16, 0.47, 0.87, 0.78, 0.19, 3.1, [1, 0.94, 0.91]],
    [0.74, 0.16, 0.65, 0.23, 0.74, 2.0, [0.91, 0.94, 1]],
    [0.12, 0.91, -0.4, 0.7, 0.19, 4.5, [1, 0.95, 0.86]],
    [-0.26, 0.5, -0.83, 0.29, 0.44, 2.2, [1, 0.8, 0.68]],
  ];
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const lat = (y / h - 0.5) * Math.PI,
        lon = (x / w - 0.5) * 2 * Math.PI;
      const dx = Math.cos(lon) * Math.cos(lat),
        dy = Math.sin(lat),
        dz = Math.sin(lon) * Math.cos(lat);
      const rgb = [
        0.25 + 0.1 * Math.max(0, dy),
        0.22 + 0.1 * Math.max(0, dy),
        0.205 + 0.1 * Math.max(0, dy),
      ];
      for (const [bx, by, bz, sw, sh, power, tint] of boxes) {
        const az = Math.atan2(dz, dx) - Math.atan2(bz, bx),
          du = Math.atan2(Math.sin(az), Math.cos(az));
        const dv = lat - Math.asin(by);
        const light =
          Math.exp(-Math.pow(Math.abs(du) / sw, 4) - Math.pow(Math.abs(dv) / sh, 4)) * power;
        for (let k = 0; k < 3; k++) rgb[k] += light * tint[k];
      }
      const i = (y * w + x) * 4;
      values.set([...rgb, 1], i);
    }
  const tex = new THREE.DataTexture(values, w, h, THREE.RGBAFormat, THREE.FloatType);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.needsUpdate = true;
  const gen = new THREE.PMREMGenerator(renderer),
    map = gen.fromEquirectangular(tex);
  tex.dispose();
  gen.dispose();
  return map;
}
function shadow() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const ctx = c.getContext('2d'),
    g = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, 'rgba(64,36,39,.58)');
  g.addColorStop(0.45, 'rgba(78,47,48,.30)');
  g.addColorStop(0.75, 'rgba(88,65,62,.09)');
  g.addColorStop(1, 'rgba(100,70,62,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(495, 207),
    new THREE.MeshBasicMaterial({
      map: new THREE.CanvasTexture(c),
      transparent: true,
      depthWrite: false,
      toneMapped: false,
    }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = -1.3;
  return mesh;
}
const modes = document.querySelectorAll('[data-mode]');
const dimButton = document.querySelector('#dimensions');
const resetButton = document.querySelector('#reset-view');
const stage = document.querySelector('#stage');
const screen = document.querySelector('#scene');
const live = document.querySelector('#viewer-status');

export function startViewer(data) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas: screen,
      antialias: true,
      alpha: true,
      powerPreference: 'low-power',
    });
  } catch {
    showFallback();
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();
  const env = environment(renderer);
  scene.environment = env.texture;
  const key = new THREE.DirectionalLight(0xffede7, 1.53);
  key.position.set(-220, 420, 330);
  scene.add(key);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, {
    left: -350,
    right: 350,
    top: 365,
    bottom: -365,
    near: 1,
    far: 1100,
  });
  key.shadow.normalBias = 0.6;
  key.shadow.bias = -0.00012;
  key.target.position.set(0, 125, 0);
  scene.add(key.target);
  const rim = new THREE.DirectionalLight(0xfff0db, 1.14);
  rim.position.set(235, 330, -115);
  scene.add(rim);
  const fill = new THREE.DirectionalLight(0xf3edff, 0.42);
  fill.position.set(260, 100, 270);
  scene.add(fill);
  const root = new THREE.Group();
  scene.add(root);
  const setForm = buildBag(root, data);
  root.traverse((o) => {
    if (o.isMesh && !o.isInstancedMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  const floor = shadow();
  scene.add(floor);
  const contact = shadow();
  contact.scale.set(0.46, 0.65, 1);
  contact.position.y = -0.85;
  scene.add(contact);
  const camera = new THREE.OrthographicCamera(-260, 260, 215, -215, 0.5, 2300);
  const ctrls = new OrbitControls(camera, screen);
  ctrls.enableDamping = true;
  ctrls.dampingFactor = 0.13;
  ctrls.enablePan = false;
  ctrls.minZoom = 0.7;
  ctrls.maxZoom = 2;
  ctrls.minPolarAngle = 0.42;
  ctrls.maxPolarAngle = Math.PI * 0.585;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let spread = 0,
    opening = 0,
    toSpread = 0,
    toOpen = 0,
    mode = 'closed',
    dims = false,
    dirty = true,
    visible = true;
  let yaw = 0.185,
    elevation = 0.13;
  function pose(a = yaw, b = elevation) {
    const centre = mode === 'open' ? 192 : 169;
    ctrls.target.set(0, centre, 0);
    camera.position.set(
      Math.sin(a) * 820 * Math.cos(b),
      centre + Math.sin(b) * 820,
      Math.cos(a) * 820 * Math.cos(b),
    );
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    ctrls.update();
    dirty = true;
  }
  pose();
  ctrls.addEventListener('change', () => {
    dirty = true;
  });
  const svg = document.querySelector('#measurements');
  const specs = [
    [[-200, -15, 65], [200, -15, 65], '400 мм', 0, 16],
    [[220, 0, 14], [220, 250, 14], '250 мм', -3, -8],
    [[-162, 14, -68], [-162, 14, 68], '136 мм', -16, -3],
  ];
  const ns = 'http://www.w3.org/2000/svg';
  const guides = specs.map(([, , label]) => {
    const group = document.createElementNS(ns, 'g'),
      line = document.createElementNS(ns, 'path'),
      txt = document.createElementNS(ns, 'text');
    txt.textContent = label;
    group.append(line, txt);
    svg.append(group);
    return { line, txt };
  });
  let width = 1,
    height = 1;
  function project(a) {
    const p = new THREE.Vector3(...a).project(camera);
    return [((p.x + 1) * width) / 2, ((1 - p.y) * height) / 2];
  }
  function drawMeasures() {
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    specs.forEach(([a, b, label, ox, oy], i) => {
      const [x, y] = project(a),
        [X, Y] = project(b),
        dx = X - x,
        dy = Y - y,
        l = Math.hypot(dx, dy) || 1,
        tx = (dy / l) * 4,
        ty = (-dx / l) * 4;
      const line = guides[i].line,
        txt = guides[i].txt;
      line.setAttribute(
        'd',
        `M${x} ${y}L${X} ${Y}M${x - tx} ${y - ty}l${2 * tx} ${2 * ty}M${X - tx} ${Y - ty}l${2 * tx} ${2 * ty}`,
      );
      txt.setAttribute('x', clamp((x + X) / 2 + ox, 25, width - 26));
      txt.setAttribute('y', clamp((y + Y) / 2 + oy, 15, height - 4));
    });
  }
  function clamp(n, min, max) {
    return Math.min(max, Math.max(min, n));
  }
  function framing() {
    const aspect = width / height,
      span = Math.max(
        407 + spread * 122 + opening * 65 + (dims ? 32 : 0),
        (486 + spread * 136 + (dims ? 65 : 0)) / aspect,
      );
    camera.top = span / 2;
    camera.bottom = -span / 2;
    camera.left = (-span * aspect) / 2;
    camera.right = (span * aspect) / 2;
    camera.updateProjectionMatrix();
  }
  function resize() {
    width = Math.max(1, stage.clientWidth);
    height = Math.max(1, stage.clientHeight);
    renderer.setSize(width, height, false);
    framing();
    dirty = true;
  }
  new ResizeObserver(resize).observe(stage);
  resize();
  new IntersectionObserver((e) => {
    visible = e[0].isIntersecting;
    if (visible) dirty = true;
  }).observe(stage);
  const labels = {
    closed: 'Вид спереди. Клапан закрыт.',
    open: 'Клапан открыт. Видны горловина и магнитная кнопка.',
    exploded: 'Детали разнесены. Виден порядок слоёв и соединений.',
  };
  function setMode(next) {
    mode = next;
    toSpread = next === 'exploded' ? 1 : 0;
    toOpen = next === 'open' ? 1 : 0;
    if (next !== 'closed' && dims) {
      dims = false;
      dimButton.setAttribute('aria-pressed', 'false');
      svg.style.display = 'none';
    }
    if (next === 'exploded') {
      pose(0.6, 0.29);
    } else if (next === 'open') {
      pose(0.64, 0.34);
    } else pose();
    modes.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === next)));
    live.textContent = labels[next];
    dirty = true;
  }
  modes.forEach((b) => b.addEventListener('click', () => setMode(b.dataset.mode)));
  dimButton.addEventListener('click', () => {
    const on = !dims;
    setMode('closed');
    dims = on;
    dimButton.setAttribute('aria-pressed', String(on));
    svg.style.display = on ? 'block' : 'none';
    if (on) pose(0.39, 0.22);
    framing();
    dirty = true;
    live.textContent = on ? 'Размеры корпуса 400 × 136 × 250 мм. С ручкой 350 мм.' : labels.closed;
  });
  resetButton.addEventListener('click', () => {
    dims = false;
    svg.style.display = 'none';
    dimButton.setAttribute('aria-pressed', 'false');
    setMode('closed');
    framing();
  });
  screen.addEventListener('keydown', (e) => {
    if (!['ArrowRight', 'ArrowLeft', 'ArrowUp', 'ArrowDown', 'Home', '+', '-', '='].includes(e.key))
      return;
    e.preventDefault();
    if (e.key === 'Home') {
      resetButton.click();
      return;
    }
    if (['+', '=', '-'].includes(e.key)) {
      camera.zoom = clamp(camera.zoom * (e.key === '-' ? 0.88 : 1.12), 0.7, 2);
      camera.updateProjectionMatrix();
    } else {
      const p = camera.position.clone().sub(ctrls.target),
        s = new THREE.Spherical().setFromVector3(p);
      s.theta += e.key === 'ArrowRight' ? 0.15 : e.key === 'ArrowLeft' ? -0.15 : 0;
      s.phi = clamp(
        s.phi + (e.key === 'ArrowUp' ? -0.11 : e.key === 'ArrowDown' ? 0.11 : 0),
        ctrls.minPolarAngle,
        ctrls.maxPolarAngle,
      );
      camera.position.copy(ctrls.target).add(new THREE.Vector3().setFromSpherical(s));
      ctrls.update();
    }
    dirty = true;
  });
  let last = performance.now();
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!visible || document.hidden) return;
    const t = reduced ? 1 : 1 - Math.exp(-8 * dt);
    if (spread !== toSpread || opening !== toOpen) {
      spread = mixForm(spread, toSpread, t);
      opening = mixForm(opening, toOpen, t);
      setForm(spread, opening);
      floor.material.opacity = 1 - 0.83 * spread;
      floor.position.y = -1.3 - spread * 71;
      contact.material.opacity = 1 - spread;
      framing();
      dirty = true;
    }
    ctrls.update();
    if (!dirty) return;
    renderer.render(scene, camera);
    if (dims) drawMeasures();
    dirty = false;
  }
  function mixForm(a, b, t) {
    const c = a + (b - a) * t;
    return Math.abs(c - b) < 0.001 ? b : c;
  }
  renderer.render(scene, camera);
  stage.dataset.ready = 'webgl';
  document.querySelector('#viewer').classList.add('ready');
  requestAnimationFrame(frame);
  screen.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    visible = false;
    showFallback();
  });
  screen.addEventListener('webglcontextrestored', () => location.reload());
}
export function showFallback() {
  screen.hidden = true;
  document.querySelector('#poster').hidden = false;
  document.querySelector('.stage-tools').hidden = true;
  document.querySelector('.view-switch').hidden = true;
  const msg = 'Статический вид модели. Интерактивное вращение требует WebGL 2.';
  live.textContent = msg;
  document.querySelector('#orbit-hint').textContent = msg;
  stage.dataset.ready = 'poster';
}
