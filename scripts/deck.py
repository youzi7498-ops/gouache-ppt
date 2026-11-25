"""Build editable gouache slides from a plan and audit reusable assets."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Pt

WIDTH, HEIGHT, UNIT = 1600, 900, 7620
BASE_TYPES = {
    "rect": MSO_AUTO_SHAPE_TYPE.RECTANGLE,
    "round": MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
    "oval": MSO_AUTO_SHAPE_TYPE.OVAL,
    "wash": MSO_AUTO_SHAPE_TYPE.RECTANGLE,
}
ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}


def xml(tag, **attributes):
    node = OxmlElement(tag)
    for key, value in attributes.items():
        node.set(key, str(value))
    return node


def emu(box):
    return [round(value * UNIT) for value in box]


def validate_box(box):
    if len(box) != 4 or not all(math.isfinite(v) for v in box) or min(box[2:]) <= 0:
        raise ValueError(f"invalid [x, y, width, height]: {box}")
    return box


def rgb(color):
    return RGBColor.from_string(color.lstrip("#").upper())


def put_picture(slide, spec, asset_root, box):
    file = asset_root / spec["file"]
    with Image.open(file) as image:
        image_w, image_h = image.size
    l, t, r, b = spec.get("clip", [0, 0, 1, 1])
    if not (0 <= l < r <= 1 and 0 <= t < b <= 1):
        raise ValueError(f"invalid crop fractions for {file}")
    x, y, w, h = box
    source_aspect = (r - l) * image_w / ((b - t) * image_h)
    frame_aspect = w / h
    fit = spec.get("fit", "contain")
    if fit == "contain":
        out_w = min(w, h * source_aspect)
        out_h = out_w / source_aspect
        box = [x + (w - out_w) / 2, y + (h - out_h) / 2, out_w, out_h]
    elif fit == "cover":
        if source_aspect > frame_aspect:
            trim = (r - l) * (1 - frame_aspect / source_aspect) / 2
            l, r = l + trim, r - trim
        else:
            trim = (b - t) * (1 - source_aspect / frame_aspect) / 2
            t, b = t + trim, b - trim
    else:
        raise ValueError(f"unsupported fit: {fit}")
    obj = slide.shapes.add_picture(str(file), *emu(box))
    obj.crop_left, obj.crop_top = l, t
    obj.crop_right, obj.crop_bottom = 1 - r, 1 - b
    if spec.get("alt"):
        obj._element.nvPicPr.cNvPr.set("descr", spec["alt"])
    return obj


def put_text(slide, spec, box, fonts):
    obj = slide.shapes.add_textbox(*emu(box))
    tf = obj.text_frame
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    margin = round(spec.get("margin", 0) * UNIT)
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = margin
    role = spec.get("role", "body")
    face = spec.get("font") or fonts.get(role)
    if not face:
        if role != "body":
            raise ValueError(f"font for role {role!r} must be set in plan fonts or in the text element")
        face = "Microsoft YaHei"
    for index, line in enumerate(spec["text"].split("\n")):
        p = tf.add_paragraph() if index else tf.paragraphs[0]
        p.alignment = ALIGN[spec.get("align", "left")]
        run = p.add_run()
        run.text = line
        run.font.name = face
        run.font.size = Pt(spec.get("size", 20))
        run.font.bold = spec.get("bold", False)
        run.font.color.rgb = rgb(spec.get("color", "233E52"))
        run._r.get_or_add_rPr().append(xml("a:ea", typeface=face))
    return obj


def tapered_geometry(props):
    props.remove(props.find(qn("a:prstGeom")))
    geom = xml("a:custGeom")
    for tag in ("avLst", "gdLst", "ahLst", "cxnLst"):
        geom.append(xml("a:" + tag))
    geom.append(xml("a:rect", l="l", t="t", r="r", b="b"))
    paths = xml("a:pathLst")
    path = xml("a:path", w=100, h=100)
    profile = [
        ("moveTo", [(0, 68)]),
        ("cubicBezTo", [(27, 55), (39, 12), (63, 16)]),
        ("cubicBezTo", [(78, 16), (88, 39), (100, 31)]),
        ("cubicBezTo", [(86, 57), (80, 76), (60, 73)]),
        ("cubicBezTo", [(42, 71), (16, 98), (0, 68)]),
        ("close", []),
    ]
    for command, points in profile:
        segment = xml("a:" + command)
        for x, y in points:
            segment.append(xml("a:pt", x=x, y=y))
        path.append(segment)
    paths.append(path)
    geom.append(paths)
    props.insert(1, geom)


def put_shape(slide, spec, box):
    kind = spec.get("kind", "rect")
    obj = slide.shapes.add_shape(BASE_TYPES[kind], *emu(box))
    props = obj._element.spPr
    style = obj._element.find(qn("p:style"))
    if style is not None:
        obj._element.remove(style)
    obj.line.fill.background()
    if spec.get("stroke"):
        obj.line.color.rgb = rgb(spec["stroke"])
        obj.line.width = Pt(spec.get("stroke_width", 1))
    opacity = spec.get("opacity", 100)
    if not 0 <= opacity <= 100:
        raise ValueError("opacity must be between 0 and 100")
    color = rgb(spec["fill"])
    if kind == "wash":
        tapered_geometry(props)
        grad = xml("a:gradFill", rotWithShape=1)
        stops = xml("a:gsLst")
        for position, strength in ((0, 0), (30000, .8), (52000, 1), (82000, .65), (100000, 0)):
            stop = xml("a:gs", pos=position)
            shade = xml("a:srgbClr", val=str(color))
            shade.append(xml("a:alpha", val=round(opacity * strength * 1000)))
            stop.append(shade)
            stops.append(stop)
        grad.append(stops)
        grad.append(xml("a:lin", ang=0, scaled=1))
        props.insert(props.index(props.find(qn("a:ln"))), grad)
    else:
        obj.fill.solid()
        obj.fill.fore_color.rgb = color
        props.find(qn("a:solidFill"))[0].append(xml("a:alpha", val=round(opacity * 1000)))
        if kind == "round":
            obj.adjustments[0] = spec.get("roundness", .11)
    return obj


def build(plan_path, output):
    if output.resolve() == plan_path.resolve() or output.suffix.lower() != ".pptx":
        raise ValueError("output must be a separate .pptx file")
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    deck = Presentation()
    deck.slide_width, deck.slide_height = emu([WIDTH, HEIGHT])
    fonts = plan.get("fonts", {})
    slides = plan["slides"]
    if not slides:
        raise ValueError("the plan contains no slides")
    for number, entry in enumerate(slides, 1):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        if entry.get("name"):
            slide.name = entry["name"]
        if entry.get("notes"):
            slide.notes_slide.notes_text_frame.text = entry["notes"]
        for index, spec in enumerate(entry["elements"], 1):
            try:
                box = validate_box(spec["box"])
                kind = spec["type"]
                if kind == "image":
                    obj = put_picture(slide, spec, plan_path.parent, box)
                elif kind == "text":
                    obj = put_text(slide, spec, box, fonts)
                elif kind == "shape":
                    obj = put_shape(slide, spec, box)
                else:
                    raise ValueError(f"unsupported element type: {kind}")
                obj.rotation = spec.get("rotation", 0)
                if spec.get("name"):
                    obj.name = spec["name"]
            except (KeyError, TypeError, ValueError, OSError) as error:
                raise ValueError(f"slide {number}, element {index}: {error}") from error
    deck.save(output)
    print(f"Built {len(slides)} slides at {output}")


def geometry(sh):
    return sh.left, sh.top, sh.width, sh.height, sh.rotation


def picture_signatures(shapes, parent=()):
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            transform = sh._element.grpSpPr.xfrm
            location = (transform.chOff.x, transform.chOff.y, transform.chExt.cx, transform.chExt.cy)
            yield from picture_signatures(sh.shapes, parent + (geometry(sh) + location,))
        elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
            crop = tuple(getattr(sh, "crop_" + side) for side in ("left", "top", "right", "bottom"))
            yield sh.image.sha1, geometry(sh), crop, parent


def preserve(before, after, exclude):
    old, new = Presentation(before), Presentation(after)
    if len(old.slides) > len(new.slides) or (old.slide_width, old.slide_height) != (
        new.slide_width, new.slide_height
    ):
        raise ValueError("source slides were removed or the canvas dimensions changed")
    if any(n < 1 or n > len(old.slides) for n in exclude):
        raise ValueError("excluded slide outside source slide range")
    failures = []
    for number, (first, second) in enumerate(zip(old.slides, new.slides), 1):
        if number in exclude:
            continue
        missing = Counter(picture_signatures(first.shapes)) - Counter(picture_signatures(second.shapes))
        if missing:
            failures.append(f"slide {number}: {sum(missing.values())} original pictures changed or missing")
    if failures:
        raise ValueError("\n".join(failures))
    print(f"Original picture assets and frames verified on {len(old.slides) - len(exclude)} slides")


def stickers(folder, minimum):
    if not folder.is_dir() or minimum < 1:
        raise ValueError("provide a sticker directory and a positive minimum")
    seen = {}
    errors = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() != ".png":
            continue
        with Image.open(path) as im:
            if im.format != "PNG" or getattr(im, "n_frames", 1) != 1:
                errors.append(f"{path.name}: expected a standalone PNG")
                continue
            image = im.convert("RGBA")
            alpha = image.getchannel("A")
            bounds = alpha.getbbox()
            low, high = alpha.getextrema()
            if low != 0 or high < 180 or bounds is None:
                errors.append(f"{path.name}: transparent background and opaque subject required")
                continue
            cropped = image.crop(bounds)
            canonical = Image.new("RGBA", cropped.size)
            canonical.alpha_composite(cropped)
            key = canonical.size, sha256(canonical.tobytes()).digest()
            if key in seen:
                errors.append(f"{path.name}: duplicate of {seen[key]}")
                continue
            seen[key] = path.name
    if len(seen) < minimum:
        errors.append(f"need {minimum} independent stickers, found {len(seen)}")
    if errors:
        raise ValueError("\n".join(errors))
    print(f"Verified {len(seen)} distinct transparent PNGs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("build")
    command.add_argument("plan", type=Path)
    command.add_argument("output", type=Path)
    command = commands.add_parser("preserve")
    command.add_argument("before", type=Path)
    command.add_argument("after", type=Path)
    command.add_argument("--exclude", default="", help="1-based source slide positions, separated by commas")
    command = commands.add_parser("stickers")
    command.add_argument("folder", type=Path)
    command.add_argument("--minimum", type=int, default=20)
    args = parser.parse_args()
    try:
        if args.command == "build":
            build(args.plan, args.output)
        elif args.command == "preserve":
            excluded = {int(n) for n in args.exclude.split(",") if n.strip()}
            preserve(args.before, args.after, excluded)
        else:
            stickers(args.folder, args.minimum)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
