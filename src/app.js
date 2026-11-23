import workshop from './workshop.json';
import { setupBudget } from './shopping.js';
const ns = 'http://www.w3.org/2000/svg';
const el = (tag, text) => {
  const e = document.createElement(tag);
  if (text) e.textContent = text;
  return e;
};
const svgEl = (tag, atts) => {
  const e = document.createElementNS(ns, tag);
  Object.entries(atts).forEach(([k, v]) => e.setAttribute(k, v));
  return e;
};
function drawPath(points, attrs, close = false) {
  const d = 'M' + points.map((p) => p.join(' ')).join('L') + (close ? 'Z' : '');
  return svgEl('path', { d, fill: 'none', ...attrs });
}
function construction(data, layouts) {
  const list = document.querySelector('#parts-list'),
    draft = document.querySelector('#draft');
  const fmt = (n) => new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 }).format(n);
  const options = document.querySelector('#layout-options'),
    materialChoice = document.querySelector('#material-choice');
  function selection(k) {
    list
      .querySelectorAll('button')
      .forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.part === k)));
  }
  function select(k) {
    options.hidden = true;
    const p = data.parts[k],
      [x, y, X, Y] = p.bbox,
      w = X - x,
      h = Y - y;
    document.querySelector('#piece-title').textContent = p.name;
    document.querySelector('#piece-note').textContent = p.note;
    document.querySelector('#piece-code').textContent = 'Деталь ' + k;
    document.querySelector('#piece-size').textContent = fmt(w) + ' × ' + fmt(h) + ' мм';
    document.querySelector('#piece-meta').textContent =
      data.materials[p.material] + ' · ' + p.qty + ' шт.';
    selection(k);
    draft.setAttribute('viewBox', [x - 10, y - 8, w + 20, h + 16].join(' '));
    draft.setAttribute('aria-label', 'Чертёж детали ' + k + ', ' + p.name);
    draft.replaceChildren(
      drawPath(
        p.cut,
        {
          stroke: '#71243a',
          'stroke-width': 1.4,
          'vector-effect': 'non-scaling-stroke',
          fill: '#c99f9123',
          'stroke-linejoin': 'round',
        },
        true,
      ),
    );
    p.marks.forEach((m) =>
      draft.append(
        drawPath(m.p, {
          stroke: ['stitch', 'trim', 'notch'].includes(m.kind) ? '#356271' : '#9c6a38',
          'stroke-width': 0.8,
          'stroke-dasharray': m.kind === 'notch' ? 'none' : m.kind === 'fold' ? '4 2 1 2' : '2 1.6',
          'vector-effect': 'non-scaling-stroke',
        }),
      ),
    );
    p.centres.forEach(([cx, cy]) => {
      draft.append(
        drawPath(
          [
            [cx - 3, cy],
            [cx + 3, cy],
          ],
          { stroke: '#9c6a38' },
        ),
        drawPath(
          [
            [cx, cy - 3],
            [cx, cy + 3],
          ],
          { stroke: '#9c6a38' },
        ),
      );
    });
  }
  function layout() {
    const material = materialChoice.value,
      lay = layouts[material],
      name = data.materials[material];
    selection('all');
    options.hidden = false;
    document.querySelector('#piece-title').textContent = 'Полная раскладка';
    document.querySelector('#piece-note').textContent =
      'Все экземпляры уже разложены по материалу. Буква на контуре совпадает с обозначением на бумажном лекале.';
    document.querySelector('#piece-code').textContent = name;
    document.querySelector('#piece-size').textContent = lay.w + ' × ' + lay.h + ' мм';
    document.querySelector('#piece-meta').textContent =
      'На этом листе — ' + lay.pieces.length + ' шт.';
    document.querySelector('#cut-link').href = './downloads/' + material + '-cut.svg';
    draft.setAttribute('viewBox', [-8, -8, lay.w + 16, lay.h + 16].join(' '));
    draft.setAttribute('aria-label', 'Полная раскладка. ' + name);
    draft.replaceChildren();
    const colors = {
      A: '#e4c8c1',
      B: '#ded0bf',
      C: '#d8b9b8',
      D: '#dfcec7',
      E: '#d5b7b8',
      G: '#d9bcaf',
    };
    for (const b of lay.pieces) {
      const p = data.parts[b.key],
        [x, y, X] = p.bbox;
      const transform = (points) =>
        points.map(([px, py]) => [b.x + (b.flip ? X - px : px - x), b.y + py - y]);
      draft.append(
        drawPath(
          transform(p.cut),
          {
            fill: colors[b.key] || '#dfcec2',
            stroke: '#73374b',
            'stroke-width': 0.9,
            'vector-effect': 'non-scaling-stroke',
          },
          true,
        ),
      );
      p.marks.forEach((m) => {
        draft.append(
          drawPath(transform(m.p), {
            stroke: ['stitch', 'notch', 'trim'].includes(m.kind) ? '#6b7374' : '#a07856',
            'stroke-width': 0.42,
            'stroke-dasharray': m.kind === 'notch' ? 'none' : '3 3',
            'vector-effect': 'non-scaling-stroke',
          }),
        );
      });
      let xx = b.x + b.w / 2,
        yy = b.y + b.h / 2;
      if (b.key === 'G') yy = b.y + 8;
      if (b.key === 'B' || b.key === 'C') {
        const q = p.seam;
        [[xx, yy]] = transform([
          [q.reduce((a, v) => a + v[0], 0) / 4, q.reduce((a, v) => a + v[1], 0) / 4],
        ]);
      }
      const label = svgEl('text', {
        x: xx,
        y: yy,
        'text-anchor': 'middle',
        'dominant-baseline': 'central',
        'font-size': b.key === 'G' ? 10 : Math.min(18, b.w * 0.27),
        fill: '#58313d',
      });
      label.textContent = b.key;
      draft.append(label);
    }
  }
  const overview = el('button');
  overview.type = 'button';
  overview.dataset.part = 'all';
  overview.className = 'all-parts';
  overview.textContent = 'Весь раскрой';
  overview.addEventListener('click', layout);
  materialChoice.addEventListener('change', layout);
  list.append(overview);
  Object.entries(data.parts).forEach(([k, p]) => {
    const b = el('button');
    b.type = 'button';
    b.dataset.part = k;
    b.setAttribute('aria-label', k + ' — ' + p.name);
    b.append(el('b', k), el('span', p.name));
    b.addEventListener('click', () => select(k));
    list.append(b);
  });
  layout();
}
function plus() {
  const icon = svgEl('svg', { 'aria-hidden': 'true' });
  icon.append(svgEl('use', { href: '#plus' }));
  return icon;
}
setupBudget();
workshop.steps.forEach(([title, a, b], i) => {
  const item = el('details'),
    summary = el('summary');
  if (i === 0) item.open = true;
  summary.append(el('b', String(i + 1).padStart(2, '0')), el('span', title), plus());
  item.append(summary, el('p', a), el('p', b));
  document.querySelector('#steps-list').append(item);
});
try {
  const [data, layouts] = await Promise.all(
    ['pattern.json', 'layouts.json'].map(async (file) => {
      const response = await fetch(new URL('./' + file, import.meta.url));
      if (!response.ok) throw new Error('Не удалось загрузить чертёж.');
      return response.json();
    }),
  );
  construction(data, layouts);
  const viewer = await import('./model.js');
  viewer.startViewer(data);
} catch (error) {
  console.error(error);
  document.querySelector('#viewer-status').textContent = 'Доступны чертёж, PDF и комплект файлов.';
  document.querySelector('#scene').hidden = true;
  document.querySelector('.stage-tools').hidden = true;
  document.querySelector('.view-switch').hidden = true;
  document.querySelector('#orbit-hint').textContent = 'Фронтальный вид';
}
