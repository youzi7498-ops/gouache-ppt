#!/usr/bin/env node
// Modified for Gouache Picture-book PPT. See NOTICE.
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
          // try next candidate
        }
      }
    }
  }
  throw new Error(`Missing Node package "${name}". Use load_workspace_dependencies and set CODEX_NODE_MODULES to the returned node_modules path.`);
}

function parseArgs(argv) {
  const args = { images: [], aspectTolerance: 0.015, thumbWidth: 720, proofsheetCols: 3, proofsheetRows: 2 };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--images") {
      i += 1;
      while (i < argv.length && !argv[i].startsWith("--")) {
        args.images.push(argv[i]);
        i += 1;
      }
      i -= 1;
    } else if (arg === "--out") {
      args.out = argv[++i];
    } else if (arg === "--contact-sheet") {
      args.contactSheet = argv[++i];
    } else if (arg === "--proofsheet-pptx") {
      args.proofsheetPptx = argv[++i];
    } else if (arg === "--proofsheet-cols") {
      args.proofsheetCols = Number(argv[++i]);
    } else if (arg === "--proofsheet-rows") {
      args.proofsheetRows = Number(argv[++i]);
    } else if (arg === "--aspect-tolerance") {
      args.aspectTolerance = Number(argv[++i]);
    } else if (arg === "--thumb-width") {
      args.thumbWidth = Number(argv[++i]);
    } else if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!args.images.length || (!args.out && !args.contactSheet && !args.proofsheetPptx)) {
    printHelp();
    process.exit(2);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
node pack_image_deck.mjs --images "images/slide_*.png" --out outputs/deck.pptx --contact-sheet outputs/contact_sheet.png
node pack_image_deck.mjs --images "images/slide_*.png" --proofsheet-pptx outputs/proofsheet.pptx

Options:
  --images            One or more image paths or simple glob patterns.
  --out               Optional full-slide image PPTX path.
  --contact-sheet     Optional contact sheet PNG path.
  --proofsheet-pptx   Optional PPTX containing thumbnail proof pages.
  --proofsheet-cols   Thumbnail columns per proofsheet slide, default 3.
  --proofsheet-rows   Thumbnail rows per proofsheet slide, default 2.
  --aspect-tolerance  Allowed deviation from 16:9, default 0.015.
  --thumb-width       Contact sheet thumbnail width, default 720.`);
}

function globToRegex(pattern) {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
  return new RegExp(`^${escaped}$`);
}

function expandOne(pattern) {
  if (!pattern.includes("*")) {
    return fs.existsSync(pattern) ? [path.resolve(pattern)] : [];
  }
  const dir = path.resolve(path.dirname(pattern));
  const base = path.basename(pattern);
  if (!fs.existsSync(dir)) return [];
  const regex = globToRegex(base);
  return fs
    .readdirSync(dir)
    .filter((name) => regex.test(name))
    .sort()
    .map((name) => path.join(dir, name));
}

function expandImages(patterns) {
  const seen = new Set();
  const paths = [];
  for (const pattern of patterns) {
    for (const imagePath of expandOne(pattern)) {
      if (!seen.has(imagePath)) {
        paths.push(imagePath);
        seen.add(imagePath);
      }
    }
  }
  return paths;
}

async function validateAspect(sharp, imagePaths, tolerance) {
  const bad = [];
  for (const imagePath of imagePaths) {
    const meta = await sharp(imagePath).metadata();
    const ratio = meta.width / meta.height;
    if (Math.abs(ratio - 16 / 9) > tolerance) {
      bad.push(`${imagePath} (${ratio.toFixed(4)})`);
    }
  }
  if (bad.length) {
    throw new Error(`Images are not close to 16:9:\n${bad.join("\n")}`);
  }
}

async function makePptx(PptxGenJS, imagePaths, outPath) {
  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: "IMAGE_WIDE", width: 13.333333, height: 7.5 });
  pptx.layout = "IMAGE_WIDE";
  pptx.author = "水粉绘本 PPT";
  pptx.subject = "水粉绘本 PPT 图片版";
  pptx.title = path.basename(outPath, path.extname(outPath));
  for (const imagePath of imagePaths) {
    const slide = pptx.addSlide();
    slide.background = { color: "FFFFFF" };
    slide.addImage({ path: imagePath, x: 0, y: 0, w: 13.333333, h: 7.5 });
  }
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await pptx.writeFile({ fileName: outPath });
}

async function makeProofsheetPptx(PptxGenJS, imagePaths, outPath, cols, rows) {
  const pptx = new PptxGenJS();
  const slideW = 13.333333;
  const slideH = 7.5;
  pptx.defineLayout({ name: "IMAGE_WIDE", width: slideW, height: slideH });
  pptx.layout = "IMAGE_WIDE";
  pptx.author = "水粉绘本 PPT";
  pptx.subject = "水粉绘本 PPT 缩略校样";
  pptx.title = path.basename(outPath, path.extname(outPath));

  const safeCols = Math.max(1, Math.floor(cols || 3));
  const safeRows = Math.max(1, Math.floor(rows || 2));
  const perPage = safeCols * safeRows;
  const marginX = 0.36;
  const marginTop = 0.42;
  const marginBottom = 0.28;
  const gapX = 0.18;
  const gapY = 0.22;
  const labelH = 0.20;
  const cellW = (slideW - marginX * 2 - gapX * (safeCols - 1)) / safeCols;
  const thumbH = cellW * 9 / 16;
  const maxThumbH = (slideH - marginTop - marginBottom - gapY * (safeRows - 1) - labelH * safeRows) / safeRows;
  const finalThumbH = Math.min(thumbH, maxThumbH);
  const finalThumbW = finalThumbH * 16 / 9;

  for (let pageStart = 0; pageStart < imagePaths.length; pageStart += perPage) {
    const slide = pptx.addSlide();
    slide.background = { color: "FFFFFF" };
    slide.addText(`Proofsheet ${Math.floor(pageStart / perPage) + 1}`, {
      x: marginX,
      y: 0.12,
      w: slideW - marginX * 2,
      h: 0.22,
      fontFace: "Arial",
      fontSize: 9,
      color: "5B667A",
      margin: 0,
      isTextBox: true,
    });
    const pageImages = imagePaths.slice(pageStart, pageStart + perPage);
    for (let i = 0; i < pageImages.length; i += 1) {
      const globalIndex = pageStart + i + 1;
      const row = Math.floor(i / safeCols);
      const col = i % safeCols;
      const x = marginX + col * (cellW + gapX) + (cellW - finalThumbW) / 2;
      const y = marginTop + row * (finalThumbH + labelH + gapY);
      slide.addText(`${String(globalIndex).padStart(2, "0")}  ${path.basename(pageImages[i])}`, {
        x,
        y,
        w: finalThumbW,
        h: labelH,
        fontFace: "Arial",
        fontSize: 6.5,
        color: "172033",
        margin: 0,
        fit: "shrink",
        isTextBox: true,
      });
      slide.addImage({ path: pageImages[i], x, y: y + labelH, w: finalThumbW, h: finalThumbH });
      slide.addShape(pptx.ShapeType.rect, {
        x,
        y: y + labelH,
        w: finalThumbW,
        h: finalThumbH,
        fill: { color: "FFFFFF", transparency: 100 },
        line: { color: "E8EDF2", width: 0.5 },
      });
    }
  }
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await pptx.writeFile({ fileName: outPath });
}

function labelSvg(width, height, text) {
  const safe = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return Buffer.from(`<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="white"/>
  <text x="0" y="24" font-family="Arial, Helvetica, sans-serif" font-size="22" fill="#172033">${safe}</text>
</svg>`);
}

async function makeContactSheet(sharp, imagePaths, outPath, thumbWidth) {
  const thumbs = [];
  for (let i = 0; i < imagePaths.length; i += 1) {
    const imagePath = imagePaths[i];
    const thumb = await sharp(imagePath).resize({ width: thumbWidth }).jpeg({ quality: 90 }).toBuffer();
    const meta = await sharp(thumb).metadata();
    thumbs.push({ imagePath, thumb, width: meta.width, height: meta.height, index: i + 1 });
  }
  const cols = thumbs.length <= 6 ? 2 : 3;
  const labelH = 34;
  const gap = 24;
  const cellW = thumbWidth;
  const cellH = thumbs[0].height + labelH;
  const rows = Math.ceil(thumbs.length / cols);
  const sheetW = cols * cellW + (cols + 1) * gap;
  const sheetH = rows * cellH + (rows + 1) * gap;
  const composites = [];
  for (const item of thumbs) {
    const row = Math.floor((item.index - 1) / cols);
    const col = (item.index - 1) % cols;
    const left = gap + col * (cellW + gap);
    const top = gap + row * (cellH + gap);
    composites.push({
      input: labelSvg(cellW, labelH, `${String(item.index).padStart(2, "0")}  ${path.basename(item.imagePath)}`),
      left,
      top,
    });
    composites.push({ input: item.thumb, left, top: top + labelH });
  }
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await sharp({ create: { width: sheetW, height: sheetH, channels: 3, background: "white" } })
    .composite(composites)
    .png()
    .toFile(outPath);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const PptxGenJS = requirePackage("pptxgenjs");
  const sharp = requirePackage("sharp");
  const imagePaths = expandImages(args.images);
  if (!imagePaths.length) {
    throw new Error("No images matched --images.");
  }
  await validateAspect(sharp, imagePaths, args.aspectTolerance);
  if (args.out) {
    await makePptx(PptxGenJS, imagePaths, path.resolve(args.out));
  }
  if (args.contactSheet) {
    await makeContactSheet(sharp, imagePaths, path.resolve(args.contactSheet), args.thumbWidth);
  }
  if (args.proofsheetPptx) {
    await makeProofsheetPptx(
      PptxGenJS,
      imagePaths,
      path.resolve(args.proofsheetPptx),
      args.proofsheetCols,
      args.proofsheetRows
    );
  }
  console.log(`slides=${imagePaths.length}`);
  if (args.out) {
    console.log(`pptx=${path.resolve(args.out)}`);
  }
  if (args.contactSheet) {
    console.log(`contact_sheet=${path.resolve(args.contactSheet)}`);
  }
  if (args.proofsheetPptx) {
    console.log(`proofsheet_pptx=${path.resolve(args.proofsheetPptx)}`);
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
