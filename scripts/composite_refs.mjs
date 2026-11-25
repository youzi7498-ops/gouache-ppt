#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

function requirePackage(name) {
  const localRequire = createRequire(import.meta.url);
  try {
    return localRequire(name);
  } catch {
    const candidates = [
      process.env.CODEX_NODE_MODULES,
      process.env.NODE_PATH,
      path.resolve(path.dirname(process.execPath), "..", "node_modules"),
    ].filter(Boolean);
    for (const root of candidates) {
      for (const dir of root.split(path.delimiter)) {
        try {
          return createRequire(path.join(dir, "noop.js"))(name);
        } catch {
          // continue
        }
      }
    }
  }
  throw new Error(`Missing Node package "${name}". Use load_workspace_dependencies and set CODEX_NODE_MODULES.`);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--spec") args.spec = argv[++i];
    else if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!args.spec) {
    printHelp();
    process.exit(2);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
node composite_refs.mjs --spec slide_04_composite.json

Spec:
{
  "base": "images/slide_04_base.png",
  "out": "images/slide_04.png",
  "canvas": [2560, 1440],
  "placements": [
    {"image": "assets/reference_images/result.png", "box": [0.10, 0.22, 0.55, 0.58], "fit": "contain", "background": "#FFFFFF", "border": "#E8EDF2"}
  ]
}

The box is [x, y, width, height] in fractions of the canvas.`);
}

function resolve(baseDir, maybePath) {
  return path.isAbsolute(maybePath) ? maybePath : path.join(baseDir, maybePath);
}

function hexToRgba(hex) {
  const clean = String(hex || "#FFFFFF").replace("#", "");
  const value = clean.length === 3 ? clean.split("").map((x) => x + x).join("") : clean;
  const num = Number.parseInt(value, 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255, alpha: 1 };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const sharp = requirePackage("sharp");
  const specPath = path.resolve(args.spec);
  const baseDir = path.dirname(specPath);
  const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
  const basePath = resolve(baseDir, spec.base);
  const outPath = resolve(baseDir, spec.out);
  const canvas = spec.canvas || [2560, 1440];
  const composites = [];

  for (const item of spec.placements || []) {
    const imagePath = resolve(baseDir, item.image);
    const [fx, fy, fw, fh] = item.box;
    const left = Math.round(fx * canvas[0]);
    const top = Math.round(fy * canvas[1]);
    const width = Math.round(fw * canvas[0]);
    const height = Math.round(fh * canvas[1]);
    const fit = item.fit || "contain";
    const background = hexToRgba(item.background || "#FFFFFF");
    const borderColor = item.border || null;
    const borderWidth = item.borderWidth == null ? 2 : Number(item.borderWidth);
    let layer = await sharp(imagePath)
      .resize({ width, height, fit, background })
      .extend({ top: 0, bottom: 0, left: 0, right: 0, background })
      .png()
      .toBuffer();
    if (borderColor) {
      const border = Buffer.from(`<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
        <rect x="${borderWidth / 2}" y="${borderWidth / 2}" width="${width - borderWidth}" height="${height - borderWidth}" fill="none" stroke="${borderColor}" stroke-width="${borderWidth}"/>
      </svg>`);
      layer = await sharp(layer).composite([{ input: border, left: 0, top: 0 }]).png().toBuffer();
    }
    composites.push({ input: layer, left, top });
  }

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await sharp(basePath).resize(canvas[0], canvas[1], { fit: "fill" }).composite(composites).png().toFile(outPath);
  console.log(JSON.stringify({ ok: true, out: outPath, placements: composites.length }));
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
