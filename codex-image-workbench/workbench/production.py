from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageOps

from .util import WorkbenchError, sha256_file


ROUTES = {"deterministic", "composite", "concept_only", "blocked"}
REQUESTED_ROUTES = {"auto", "deterministic", "composite", "concept_only"}
HARD_STOP_FAILURES = {"product_identity", "product_geometry", "product_proportion"}
FAILURE_CLASSES = HARD_STOP_FAILURES | {
    "composition",
    "background",
    "typography",
    "technical",
    "other",
}


def _bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def image_has_transparency(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            if image.mode in {"RGBA", "LA"}:
                alpha = image.getchannel("A")
                minimum, _ = alpha.getextrema()
                return minimum < 255
            if image.mode == "P" and "transparency" in image.info:
                return True
    except (OSError, ValueError):
        return False
    return False


def normalize_production_spec(
    raw: dict[str, Any] | None,
    references: dict[str, dict[str, Any]],
    reference_ids: list[str],
    required_views: list[str] | None = None,
    scene_required: bool = False,
) -> dict[str, Any]:
    value = copy.deepcopy(raw or {})
    requested = str(value.get("requested_route", "auto")).strip().lower()
    if requested not in REQUESTED_ROUTES:
        raise WorkbenchError(f"invalid production route: {requested}")

    exact_product = _bool(value.get("exact_product_required"), True)
    pixel_policy = "locked" if exact_product else "generated_allowed"
    required = [str(item).strip() for item in (required_views or []) if str(item).strip()]
    target_view = str(value.get("target_view") or (required[0] if required else "")).strip()
    scene_required = _bool(value.get("scene_required"), scene_required)
    blockers: list[str] = []
    warnings: list[str] = []
    capture_requests: list[dict[str, str]] = []

    product_refs = []
    for reference_id in reference_ids:
        reference = references.get(reference_id)
        if not reference or reference.get("role") != "product":
            continue
        if not reference.get("approved", False):
            continue
        if not reference.get("exists", False) or not reference.get("readable_image", False):
            continue
        if target_view and reference.get("view") != target_view:
            continue
        product_refs.append(reference)

    selected_id = str(value.get("product_source_id", "")).strip()
    selected = None
    if selected_id:
        selected = next((item for item in product_refs if item.get("reference_id") == selected_id), None)
        if selected is None:
            blockers.append(f"product source is not an approved readable {target_view or 'required-view'} reference: {selected_id}")
    elif product_refs:
        selected = product_refs[0]
        selected_id = str(selected.get("reference_id", ""))

    selected_path = ""
    transparent = False
    if exact_product:
        if selected is None:
            label = target_view or "required-view"
            blockers.append(f"missing approved product source for {label}")
            capture_requests.append(
                {
                    "key": label,
                    "action": "capture_or_approve_product_view",
                    "message": f"Provide and approve a clear {label} product image.",
                }
            )
        else:
            selected_path = str(selected.get("path", ""))
            transparent = image_has_transparency(Path(selected_path))

    route = requested
    if route == "auto":
        route = "composite" if scene_required else "deterministic"
    if requested == "concept_only" and exact_product:
        blockers.append("concept-only generation cannot satisfy exact product identity")
    if route in {"deterministic", "composite"} and not exact_product:
        blockers.append("locked-product route requires exact_product_required=true")

    background_path = str(value.get("background_source_path", "")).strip()
    background_product_free = _bool(value.get("background_product_free_reviewed"), False)
    source_quality = str(value.get("source_quality", "approved")).strip().lower()
    if source_quality not in {"approved", "needs_review", "insufficient"}:
        raise WorkbenchError("production source_quality must be approved, needs_review, or insufficient")
    if exact_product and source_quality != "approved":
        blockers.append(f"product source quality is {source_quality}")
        capture_requests.append(
            {
                "key": selected_id or target_view or "product",
                "action": "reshoot_or_recut_product_source",
                "message": "Supply a clean, correctly proportioned product source and approve it for production.",
            }
        )
    if exact_product and route in {"deterministic", "composite"} and selected is not None and not transparent:
        blockers.append("locked product source must be a transparent cutout")
        capture_requests.append(
            {
                "key": selected_id or target_view or "product",
                "action": "prepare_transparent_cutout",
                "message": "Prepare a reviewed transparent PNG cutout from the real product photo.",
            }
        )
    if route == "composite":
        if not background_path or not Path(background_path).expanduser().is_file():
            blockers.append("composite route requires an existing background source")
            capture_requests.append(
                {
                    "key": "background",
                    "action": "generate_or_supply_background_only",
                    "message": "Generate or supply a background without the product, then rerun the gate.",
                }
            )
        if not background_product_free:
            blockers.append("composite background must be reviewed as product-free")
    if route == "concept_only" and exact_product:
        route = "blocked"
    if blockers:
        route = "blocked"
    if not exact_product and requested == "auto":
        route = "concept_only"
        warnings.append("Concept-only output is not eligible for direct Listing or A+ release.")

    canvas = copy.deepcopy(value.get("canvas") or {})
    canvas["width"] = int(canvas.get("width", 1254))
    canvas["height"] = int(canvas.get("height", 1254))
    canvas["background"] = str(canvas.get("background", "#FFFFFF"))
    if canvas["width"] < 64 or canvas["height"] < 64:
        raise WorkbenchError("production canvas must be at least 64x64")

    placement = copy.deepcopy(value.get("placement") or {})
    placement["max_width_ratio"] = float(placement.get("max_width_ratio", 0.82))
    placement["max_height_ratio"] = float(placement.get("max_height_ratio", 0.82))
    placement["anchor"] = str(placement.get("anchor", "center"))
    placement["offset_x"] = int(placement.get("offset_x", 0))
    placement["offset_y"] = int(placement.get("offset_y", 0))
    if not 0.05 <= placement["max_width_ratio"] <= 1 or not 0.05 <= placement["max_height_ratio"] <= 1:
        raise WorkbenchError("production placement ratios must be between 0.05 and 1")

    return {
        "schema_version": "production-route.1",
        "requested_route": requested,
        "route": route,
        "exact_product_required": exact_product,
        "product_pixel_policy": pixel_policy,
        "scene_required": scene_required,
        "target_view": target_view,
        "product_source_id": selected_id,
        "product_source_path": selected_path,
        "product_source_has_transparency": transparent,
        "source_quality": source_quality,
        "background_source_path": background_path,
        "background_product_free_reviewed": background_product_free,
        "canvas": canvas,
        "placement": placement,
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "capture_requests": capture_requests,
    }


def validate_job_production(
    raw: dict[str, Any] | None,
    references: list[dict[str, Any]],
    execution_mode: str,
) -> dict[str, Any]:
    if raw is None:
        return {
            "schema_version": "legacy",
            "route": "legacy",
            "requested_route": "legacy",
            "exact_product_required": None,
            "product_pixel_policy": "unverified",
            "blockers": [],
            "warnings": ["Legacy job did not pass the V1.3 production route gate."],
            "capture_requests": [],
        }
    normalized_refs: dict[str, dict[str, Any]] = {}
    ids: list[str] = []
    for index, raw_reference in enumerate(references):
        reference = copy.deepcopy(raw_reference)
        reference_id = str(reference.get("reference_id") or f"job-ref-{index + 1}")
        path = Path(str(reference.get("path", ""))).expanduser()
        reference.update(
            {
                "reference_id": reference_id,
                "role": str(reference.get("role", "product")),
                "view": str(reference.get("view", "")),
                "approved": _bool(reference.get("approved"), True),
                "exists": path.is_file(),
                "readable_image": path.is_file(),
                "path": str(path),
            }
        )
        normalized_refs[reference_id] = reference
        ids.append(reference_id)
    value = normalize_production_spec(raw, normalized_refs, ids)
    if value["route"] in {"deterministic", "composite"} and execution_mode != "manual_import":
        value["blockers"].append("locked-product routes require manual_import execution mode")
        value["route"] = "blocked"
    if value["route"] == "concept_only" and execution_mode != "codex_auto":
        value["warnings"].append("Concept-only jobs normally use codex_auto execution.")
    return value


def compose_locked_product(production: dict[str, Any], output_path: Path) -> dict[str, Any]:
    route = production.get("route")
    if route not in {"deterministic", "composite"}:
        raise WorkbenchError("deterministic compositor only accepts deterministic or composite routes")
    if production.get("blockers"):
        raise WorkbenchError("production route is blocked: " + "; ".join(production["blockers"]))
    source = Path(str(production.get("product_source_path", ""))).expanduser().resolve()
    if not source.is_file() or not image_has_transparency(source):
        raise WorkbenchError("deterministic compositor requires a transparent product PNG")

    canvas_spec = production["canvas"]
    width, height = int(canvas_spec["width"]), int(canvas_spec["height"])
    background_path = str(production.get("background_source_path", "")).strip()
    if background_path:
        with Image.open(Path(background_path).expanduser()) as background_image:
            canvas = ImageOps.fit(background_image.convert("RGB"), (width, height), Image.Resampling.LANCZOS).convert("RGBA")
    else:
        try:
            color = ImageColor.getrgb(str(canvas_spec.get("background", "#FFFFFF")))
        except ValueError as exc:
            raise WorkbenchError("invalid production canvas background color") from exc
        canvas = Image.new("RGBA", (width, height), (*color, 255))

    with Image.open(source) as product_image:
        product = product_image.convert("RGBA")
    bbox = product.getbbox()
    if not bbox:
        raise WorkbenchError("product source is fully transparent")
    product = product.crop(bbox)
    placement = production["placement"]
    max_width = max(1, round(width * float(placement["max_width_ratio"])))
    max_height = max(1, round(height * float(placement["max_height_ratio"])))
    scale = min(max_width / product.width, max_height / product.height)
    target = (max(1, round(product.width * scale)), max(1, round(product.height * scale)))
    product = product.resize(target, Image.Resampling.LANCZOS)

    anchor = placement.get("anchor", "center")
    x = (width - product.width) // 2
    y = (height - product.height) // 2
    if anchor == "bottom-center":
        y = height - product.height
    elif anchor == "top-center":
        y = 0
    elif anchor not in {"center", "bottom-center", "top-center"}:
        raise WorkbenchError(f"unsupported production anchor: {anchor}")
    x += int(placement.get("offset_x", 0))
    y += int(placement.get("offset_y", 0))
    if x < 0 or y < 0 or x + product.width > width or y + product.height > height:
        raise WorkbenchError("product placement falls outside the canvas")
    canvas.alpha_composite(product, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, format="PNG", optimize=True)
    return {
        "schema_version": "production-provenance.1",
        "route": route,
        "generated_product_pixels": False,
        "product_source_path": str(source),
        "product_source_sha256": sha256_file(source),
        "background_source_path": str(Path(background_path).expanduser().resolve()) if background_path else "",
        "background_source_sha256": sha256_file(Path(background_path).expanduser()) if background_path else "",
        "canvas": {"width": width, "height": height},
        "product_bounds": {"x": x, "y": y, "width": product.width, "height": product.height},
        "resampling": "lanczos",
    }
