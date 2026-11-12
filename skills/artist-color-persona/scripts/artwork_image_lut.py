"""Prepare a photo and an actual artwork for Image, then fit its returned photo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import copyfile
from struct import pack


SKILL = Path(__file__).resolve().parents[1]
from color_match_lut import digest, json_write, read_srgb, run_fit, srgb_profile
from losses import screen_geometry


PROMPT = "Image 1 is the content photo. Image 2 is the color reference. Match the colors of Image 1 to Image 2."


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(path):
    return {"path": str(path.resolve()), "sha256": digest(path)}


def checked(record):
    path = Path(record["path"])
    if digest(path) != record["sha256"]:
        raise ValueError(f"Archived input changed: {path}")
    return path


def prepare(content, artwork, output, artist, title, reason, source, edge):
    cards = read_json(SKILL / "references/personas.json")
    card = next((card for card in cards if card["id"] == artist), None)
    if card is None:
        raise ValueError(f"Unknown artist card: {artist}")
    if content.samefile(artwork) or digest(content) == digest(artwork):
        raise ValueError("Supply a separate artwork as the color reference")
    original = artifact(content)
    reference = artifact(artwork)
    photo, photo_info = read_srgb(content, long_edge=edge)
    painting, painting_info = read_srgb(artwork, long_edge=edge)
    if artifact(content) != original or artifact(artwork) != reference:
        raise ValueError("An input file changed during preparation")
    output.mkdir(parents=True)
    # LittleCMS otherwise adds the current time to the profile header.
    profile = srgb_profile()
    profile = profile[:24] + pack(">6H", 2026, 1, 1, 0, 0, 0) + profile[36:]
    upload, ref = output / "content.jpg", output / "artwork-reference.png"
    photo.save(upload, quality=85, optimize=True, subsampling=0, icc_profile=profile)
    painting.save(ref, icc_profile=profile)
    archived = output / ("artwork-original" + artwork.suffix.lower())
    copyfile(artwork, archived)
    if digest(archived) != reference["sha256"]:
        raise ValueError("Artwork changed during archiving")
    prompt = output / "prompt.txt"
    prompt.write_text(PROMPT, encoding="utf-8")
    job = {
        "artist": {"id": artist, "name": card["artist"], "dossier": card.get("dossier")},
        "artwork": {"title": title, "source": source, "selection_reason": reason,
                    "original": reference, "archived": artifact(archived), "preparation": painting_info},
        "original": {**original, "oriented_size": photo_info["source_size"]},
        "upload": {**artifact(upload), "size": list(photo.size)},
        "reference": {**artifact(ref), "size": list(painting.size)},
        "prompt": artifact(prompt), "image_inputs": [str(upload), str(ref)],
        "monochrome": artist == "adams_zone_print",
    }
    json_write(output / "job.json", job)
    return job


def finish(job_path, returned):
    job = read_json(job_path)
    folder = job_path.parent
    original, upload, reference = (checked(job[key]) for key in ("original", "upload", "reference"))
    checked(job["artwork"]["archived"])
    prompt = checked(job["prompt"])
    if job["image_inputs"] != [str(upload), str(reference)] or prompt.read_text(encoding="utf-8") != PROMPT:
        raise ValueError("Job no longer contains the prepared two-image request")
    if digest(returned) in {job[key]["sha256"] for key in ("original", "upload", "reference")} | {job["artwork"]["archived"]["sha256"]}:
        raise ValueError("Supply the actual Image return, separate from the photo and artwork inputs")
    archived = folder / ("image-return" + returned.suffix.lower())
    returns = list(folder.glob("image-return.*"))
    if returns and (returns != [archived] or digest(archived) != digest(returned)):
        raise FileExistsError("Use a new job folder for a different Image return")
    if not archived.exists():
        copyfile(returned, archived)
    geometry = screen_geometry(upload, archived)
    target = artifact(archived)
    fit_path = folder / "fit"
    run_path = fit_path / "run.json"
    if run_path.exists():
        report = read_json(run_path)
        if report["content"][0]["sha256"] != job["upload"]["sha256"] or report["style"][0]["sha256"] != target["sha256"]:
            raise ValueError("Existing fit has different inputs")
    else:
        report = run_fit([upload], [archived], fit_path, methods=("bures",),
                         fit_edge=max(job["upload"]["size"]), apply_paths=(original,),
                         overwrite=fit_path.exists(), monochrome=job["monochrome"])
    result = report["methods"]["bures"]
    render = result["renders"][0]
    bit_depth = render["output_bit_depth"]
    if (render["output_size"] != job["original"]["oriented_size"]
            or render[f"png_lut_verification_max_error_{bit_depth}bit"] != 0
            or digest(Path(result["cube"])) != result["cube_sha256"]):
        raise ValueError("Saved LUT render did not verify at the original resolution")
    record = {"job": str(job_path), "image_return": target, "geometry": geometry,
              "fit_scope": "global_color_statistics" if geometry["passed"] else "global_color_statistics_only_after_geometry_failure",
              "fit_report": str(run_path), "lut": artifact(Path(result["cube"])),
              "render": {**artifact(Path(render["png"])), "preview": render["preview"], "size": render["output_size"]},
              "persona_input": {"artist": job["artist"], "artwork": job["artwork"], "original": str(original),
                                "reference": str(reference), "image_return": str(archived), "lut_render": render["png"]}}
    json_write(folder / "result.json", record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--content", type=Path, required=True)
    p.add_argument("--artwork", type=Path, required=True)
    p.add_argument("--artist", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--source", required=True, help="Original source URL or user attachment")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--edge", type=int, default=720)
    f = sub.add_parser("finish")
    f.add_argument("--job", type=Path, required=True)
    f.add_argument("--styled", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        if args.edge < 16:
            parser.error("--edge must be at least 16")
        output = args.output.resolve()
        prepare(args.content.resolve(), args.artwork.resolve(), output, args.artist, args.title, args.reason, args.source, args.edge)
        print(output / "job.json")
    else:
        result = finish(args.job.resolve(), args.styled.resolve())
        print(json.dumps({"result": str(args.job.resolve().parent / "result.json"), "fit_scope": result["fit_scope"]}))


if __name__ == "__main__":
    main()
