import { build } from 'esbuild';
import { mkdir, copyFile, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.chdir(root);
const out = 'docs/assets';
await mkdir(out + '/fonts', { recursive: true });
const subsets = [
  ['cyrillic', 'U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116'],
  [
    'latin',
    'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD',
  ],
];
let css = '';
for (const [id, name, styles] of [
  [
    'cormorant-garamond',
    'Cormorant Garamond',
    [
      [500, 'normal'],
      [500, 'italic'],
    ],
  ],
  [
    'inter',
    'Inter',
    [
      [400, 'normal'],
      [500, 'normal'],
      [600, 'normal'],
    ],
  ],
]) {
  for (const [sub, range] of subsets)
    for (const [weight, style] of styles) {
      const f = id + '-' + sub + '-' + weight + '-' + style + '.woff2';
      await copyFile('node_modules/@fontsource/' + id + '/files/' + f, out + '/fonts/' + f);
      css += `@font-face{font-family:'${name}';font-style:${style};font-weight:${weight};font-display:swap;src:url('./fonts/${f}') format('woff2');unicode-range:${range}}\n`;
    }
  await copyFile(
    'node_modules/@fontsource/' + id + '/LICENSE',
    out + '/fonts/' + id + '-LICENSE.txt',
  );
}
await writeFile(out + '/fonts.css', css);
await copyFile('node_modules/three/LICENSE', out + '/three-LICENSE.txt');
await build({
  entryPoints: ['src/viewer.js'],
  bundle: true,
  minify: true,
  format: 'esm',
  outfile: out + '/model.js',
  target: ['es2022'],
  legalComments: 'eof',
});
// Strip incidental line-end padding in the embedded GLSL source.
const compiled = await readFile(out + '/model.js', 'utf8');
await writeFile(out + '/model.js', compiled.replace(/[ \t]+$/gm, ''));
await build({
  entryPoints: ['src/app.js'],
  bundle: true,
  minify: true,
  format: 'esm',
  outfile: out + '/app.js',
  target: ['es2022'],
  external: ['./model.js'],
});
