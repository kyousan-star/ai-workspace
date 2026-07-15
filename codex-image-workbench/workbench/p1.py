from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .util import WorkbenchError, image_metadata, sha256_file


FACT_STATUSES = {"locked", "pending", "conflict"}
CLAIM_STATUSES = {"allowed", "qualified", "prohibited", "pending"}
SELLING_POINT_STATUSES = {"candidate", "locked", "rejected"}
REFERENCE_ROLES = {"product", "detail", "in-box", "scale", "packaging", "lifestyle"}
VIEWS = {"front", "rear", "left", "right", "side", "top", "bottom", "three-quarter", "detail", "in-box", "scale"}


def require_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise WorkbenchError(f"missing P1 field: {field}")
    return text


def require_list(value: Any, field: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise WorkbenchError(f"P1 field must be a list: {field}")
    return value


def unique_records(records: list, id_field: str, field: str) -> None:
    if any(not isinstance(record, dict) for record in records):
        raise WorkbenchError(f"P1 records must be objects: {field}")
    values = [require_text(record.get(id_field), f"{field}.{id_field}") for record in records]
    if len(values) != len(set(values)):
        raise WorkbenchError(f"duplicate IDs in {field}")


def require_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise WorkbenchError(f"P1 field must be an integer: {field}") from exc


def resolve_path(raw: Any, workflow_root: Path | None) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute() and workflow_root:
        path = workflow_root / path
    return path.resolve()


def normalize_intake(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise WorkbenchError("P1 intake must be a JSON object")
    value = copy.deepcopy(payload)
    schema = value.get("schema_version", "p1-intake.1")
    if schema != "p1-intake.1":
        raise WorkbenchError("schema_version must be p1-intake.1")
    value["schema_version"] = schema

    source = value.setdefault("source", {})
    if not isinstance(source, dict):
        raise WorkbenchError("source must be an object")
    workflow_root = resolve_path(source.get("workflow_root"), None)
    if workflow_root:
        source["workflow_root"] = str(workflow_root)

    product = value.setdefault("product", {})
    if not isinstance(product, dict):
        raise WorkbenchError("product must be an object")
    product["name"] = require_text(product.get("name"), "product.name")
    product["category"] = require_text(product.get("category"), "product.category")
    facts = require_list(product.get("facts"), "product.facts")
    unique_records(facts, "fact_id", "product.facts")
    for fact in facts:
        fact["label"] = require_text(fact.get("label"), "product.facts.label")
        fact["value"] = require_text(fact.get("value"), "product.facts.value")
        fact["status"] = fact.get("status", "pending")
        if fact["status"] not in FACT_STATUSES:
            raise WorkbenchError(f"invalid fact status: {fact['status']}")
        fact["required_for_visual"] = bool(fact.get("required_for_visual", False))
        fact["source"] = str(fact.get("source", "")).strip()
    product["facts"] = facts
    product["must_show"] = [str(item).strip() for item in require_list(product.get("must_show"), "product.must_show") if str(item).strip()]
    product["must_not_show"] = [str(item).strip() for item in require_list(product.get("must_not_show"), "product.must_not_show") if str(item).strip()]

    claims = require_list(value.get("claims"), "claims")
    unique_records(claims, "claim_id", "claims")
    for claim in claims:
        claim["text"] = require_text(claim.get("text"), "claims.text")
        claim["status"] = claim.get("status", "pending")
        if claim["status"] not in CLAIM_STATUSES:
            raise WorkbenchError(f"invalid claim status: {claim['status']}")
        claim["evidence"] = str(claim.get("evidence", "")).strip()
        claim["qualifier"] = str(claim.get("qualifier", "")).strip()
        claim["selected_for_images"] = bool(claim.get("selected_for_images", False))
    value["claims"] = claims

    points = require_list(value.get("selling_points"), "selling_points")
    unique_records(points, "selling_point_id", "selling_points")
    for point in points:
        point["text"] = require_text(point.get("text"), "selling_points.text")
        point["status"] = point.get("status", "candidate")
        if point["status"] not in SELLING_POINT_STATUSES:
            raise WorkbenchError(f"invalid selling point status: {point['status']}")
        point["evidence"] = require_list(point.get("evidence"), "selling_points.evidence")
        point["visualizability"] = str(point.get("visualizability", "unknown")).strip()
    value["selling_points"] = points

    references = require_list(value.get("references"), "references")
    unique_records(references, "reference_id", "references")
    for reference in references:
        reference["role"] = str(reference.get("role", "product")).strip()
        if reference["role"] not in REFERENCE_ROLES:
            raise WorkbenchError(f"invalid reference role: {reference['role']}")
        reference["view"] = str(reference.get("view", "detail")).strip()
        if reference["view"] not in VIEWS:
            raise WorkbenchError(f"invalid reference view: {reference['view']}")
        reference["visible_features"] = [
            str(item).strip() for item in require_list(reference.get("visible_features"), "references.visible_features")
            if str(item).strip()
        ]
        reference["approved"] = bool(reference.get("approved", False))
        path = resolve_path(reference.get("path"), workflow_root)
        reference["path"] = str(path) if path else ""
        reference["exists"] = bool(path and path.is_file())
        reference["sha256"] = sha256_file(path) if reference["exists"] else None
        if reference["exists"]:
            try:
                reference["metadata"] = image_metadata(path)
                reference["readable_image"] = True
            except WorkbenchError:
                reference["metadata"] = {}
                reference["readable_image"] = False
        else:
            reference["metadata"] = {}
            reference["readable_image"] = False
    value["references"] = references

    competitors = require_list(value.get("competitors"), "competitors")
    unique_records(competitors, "competitor_id", "competitors")
    for competitor in competitors:
        competitor["name"] = require_text(competitor.get("name"), "competitors.name")
        competitor["asin_or_url"] = str(competitor.get("asin_or_url", "")).strip()
        competitor["role"] = str(competitor.get("role", "direct")).strip()
        image_paths = []
        for raw_path in require_list(competitor.get("image_paths"), "competitors.image_paths"):
            path = resolve_path(raw_path, workflow_root)
            image_paths.append({"path": str(path) if path else "", "exists": bool(path and path.is_file())})
        competitor["image_paths"] = image_paths
        listing_path = resolve_path(competitor.get("listing_path"), workflow_root)
        competitor["listing_path"] = str(listing_path) if listing_path else ""
        competitor["listing_exists"] = bool(listing_path and listing_path.is_file())
    value["competitors"] = competitors

    brand = value.setdefault("brand", {})
    if not isinstance(brand, dict):
        raise WorkbenchError("brand must be an object")
    brand["status"] = str(brand.get("status", "missing")).strip()
    if brand["status"] not in {"approved", "draft", "missing"}:
        raise WorkbenchError(f"invalid brand status: {brand['status']}")
    brand["invariants"] = [str(item).strip() for item in require_list(brand.get("invariants"), "brand.invariants") if str(item).strip()]
    brand["avoid"] = [str(item).strip() for item in require_list(brand.get("avoid"), "brand.avoid") if str(item).strip()]
    system_path = resolve_path(brand.get("system_path"), workflow_root)
    brand["system_path"] = str(system_path) if system_path else ""
    brand["system_exists"] = bool(system_path and system_path.exists())
    value["brand"] = brand

    requirements = value.setdefault("coverage_requirements", {})
    if not isinstance(requirements, dict):
        raise WorkbenchError("coverage_requirements must be an object")
    requirements["min_product_images"] = require_int(requirements.get("min_product_images", 2), "coverage_requirements.min_product_images")
    requirements["min_competitors"] = require_int(requirements.get("min_competitors", 1), "coverage_requirements.min_competitors")
    requirements["required_views"] = [str(item).strip() for item in require_list(requirements.get("required_views"), "coverage_requirements.required_views") if str(item).strip()]
    requirements["required_visible_features"] = [
        str(item).strip() for item in require_list(requirements.get("required_visible_features"), "coverage_requirements.required_visible_features")
        if str(item).strip()
    ]
    requirements["require_approved_brand"] = bool(requirements.get("require_approved_brand", True))
    if requirements["min_product_images"] < 1 or requirements["min_product_images"] > 20:
        raise WorkbenchError("min_product_images must be between 1 and 20")
    if requirements["min_competitors"] < 0 or requirements["min_competitors"] > 20:
        raise WorkbenchError("min_competitors must be between 0 and 20")
    if any(view not in VIEWS for view in requirements["required_views"]):
        raise WorkbenchError("coverage_requirements contains an invalid view")
    value["coverage_requirements"] = requirements
    return value


def capture_instruction(view: str) -> str:
    instructions = {
        "front": "Straight-on front view at product height; keep all front controls and logo readable.",
        "rear": "Straight-on rear view; expose ports, labels, hinges, or closures without hand occlusion.",
        "left": "True left-side profile on a neutral background.",
        "right": "True right-side profile on a neutral background.",
        "side": "Side profile that reveals product depth and side controls.",
        "top": "Top-down view with the full product inside frame.",
        "bottom": "Bottom view showing feet, mounts, labels, or attachment points.",
        "three-quarter": "Front three-quarter view that establishes shape and depth.",
        "detail": "Close-up with sharp focus on the requested feature and surrounding geometry.",
        "in-box": "All included items arranged separately so quantity and shape are unambiguous.",
        "scale": "Product beside a known-size object or in a natural hand/use context without hiding controls.",
    }
    return instructions.get(view, "Add a distinct product angle on a neutral background.")


def build_coverage(intake: dict[str, Any]) -> dict[str, Any]:
    strategy_blockers: list[dict[str, str]] = []
    generation_blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    capture_requests: list[dict[str, str]] = []

    for fact in intake["product"]["facts"]:
        if fact["required_for_visual"] and fact["status"] != "locked":
            strategy_blockers.append(
                {"code": "fact_not_locked", "item": fact["fact_id"], "message": f"Lock product fact: {fact['label']}"}
            )

    active_points = [point for point in intake["selling_points"] if point["status"] != "rejected"]
    if not active_points:
        strategy_blockers.append({"code": "no_selling_points", "item": "selling_points", "message": "Add at least one candidate selling point."})

    for claim in intake["claims"]:
        if not claim["selected_for_images"]:
            continue
        if claim["status"] == "pending":
            strategy_blockers.append({"code": "claim_pending", "item": claim["claim_id"], "message": f"Resolve claim: {claim['text']}"})
        elif claim["status"] == "prohibited":
            strategy_blockers.append({"code": "claim_prohibited", "item": claim["claim_id"], "message": f"Remove prohibited claim: {claim['text']}"})
        elif not claim["evidence"]:
            strategy_blockers.append({"code": "claim_missing_evidence", "item": claim["claim_id"], "message": f"Add evidence for claim: {claim['text']}"})
        elif claim["status"] == "qualified" and not claim["qualifier"]:
            strategy_blockers.append({"code": "claim_missing_qualifier", "item": claim["claim_id"], "message": f"Add qualifier for claim: {claim['text']}"})

    requirements = intake["coverage_requirements"]
    brand = intake["brand"]
    if requirements["require_approved_brand"] and brand["status"] != "approved":
        strategy_blockers.append({"code": "brand_not_approved", "item": "brand", "message": "Approve or explicitly waive the brand system before Gate 1."})

    usable = [
        reference for reference in intake["references"]
        if reference["approved"] and reference["exists"] and reference["readable_image"]
    ]
    unique_hashes = {reference["sha256"] for reference in usable if reference["sha256"]}
    shortfall = max(0, requirements["min_product_images"] - len(unique_hashes))
    if shortfall:
        generation_blockers.append(
            {"code": "insufficient_product_images", "item": "references", "message": f"Add {shortfall} distinct approved product image(s)."}
        )

    available_views = {reference["view"] for reference in usable}
    for view in requirements["required_views"]:
        if view not in available_views:
            generation_blockers.append({"code": "missing_view", "item": view, "message": f"Add an approved {view} reference image."})
            capture_requests.append({"type": "view", "key": view, "instruction": capture_instruction(view)})

    visible_features = {feature for reference in usable for feature in reference["visible_features"]}
    for feature in requirements["required_visible_features"]:
        if feature not in visible_features:
            generation_blockers.append({"code": "missing_feature_visibility", "item": feature, "message": f"Add a reference that clearly shows: {feature}."})
            capture_requests.append({"type": "detail", "key": feature, "instruction": f"Capture a sharp close-up of {feature}; include enough surrounding product geometry to verify its location."})

    for index in range(shortfall):
        capture_requests.append(
            {"type": "additional-angle", "key": f"angle-{index + 1}", "instruction": capture_instruction("three-quarter" if index % 2 == 0 else "side")}
        )

    usable_competitors = [
        competitor for competitor in intake["competitors"]
        if competitor["listing_exists"] or any(image["exists"] for image in competitor["image_paths"])
    ]
    if len(usable_competitors) < requirements["min_competitors"]:
        warnings.append(
            {"code": "competitor_shortfall", "item": "competitors", "message": f"Only {len(usable_competitors)} usable competitor package(s); target is {requirements['min_competitors']}."}
        )

    strategy_status = "blocked" if strategy_blockers else "passed"
    generation_status = "blocked" if strategy_blockers or generation_blockers else "passed"
    status = "blocked" if generation_status == "blocked" else ("warning" if warnings else "passed")
    return {
        "status": status,
        "strategy_status": strategy_status,
        "generation_status": generation_status,
        "strategy_blockers": strategy_blockers,
        "generation_blockers": generation_blockers,
        "warnings": warnings,
        "capture_requests": capture_requests,
        "metrics": {
            "facts": len(intake["product"]["facts"]),
            "claims": len(intake["claims"]),
            "selling_points": len(active_points),
            "references": len(intake["references"]),
            "usable_distinct_product_images": len(unique_hashes),
            "competitors": len(intake["competitors"]),
            "usable_competitors": len(usable_competitors),
        },
    }


def validate_strategy(intake: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(payload)
    order = [str(item).strip() for item in require_list(value.get("selling_point_order"), "strategy.selling_point_order") if str(item).strip()]
    if not order or len(order) != len(set(order)):
        raise WorkbenchError("strategy selling_point_order must contain unique IDs")
    available = {point["selling_point_id"] for point in intake["selling_points"] if point["status"] != "rejected"}
    if any(item not in available for item in order):
        raise WorkbenchError("strategy references an unknown or rejected selling point")
    value["selling_point_order"] = order
    baselines = require_list(value.get("category_baselines"), "strategy.category_baselines")
    unique_records(baselines, "baseline_id", "strategy.category_baselines")
    for baseline in baselines:
        baseline["label"] = require_text(baseline.get("label"), "strategy.category_baselines.label")
        baseline["required"] = bool(baseline.get("required", False))
        baseline["source"] = str(baseline.get("source", "")).strip()
    value["category_baselines"] = baselines
    for field in ("rejected_techniques", "competitive_pitfalls", "compliance_boundaries", "visual_exclusions"):
        value[field] = [str(item).strip() for item in require_list(value.get(field), f"strategy.{field}") if str(item).strip()]
    claim_ids = [str(item).strip() for item in require_list(value.get("claim_ids"), "strategy.claim_ids") if str(item).strip()]
    claims = {claim["claim_id"]: claim for claim in intake["claims"]}
    for claim_id in claim_ids:
        claim = claims.get(claim_id)
        if not claim or claim["status"] not in {"allowed", "qualified"} or not claim["evidence"]:
            raise WorkbenchError(f"strategy claim is not usable: {claim_id}")
    value["claim_ids"] = claim_ids
    return value


def validate_sequence(strategy: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(payload)
    slots = require_list(value.get("slots"), "sequence.slots")
    if not slots:
        raise WorkbenchError("sequence requires at least one slot")
    unique_records(slots, "slot_key", "sequence.slots")
    positions = []
    selling_points = set(strategy["selling_point_order"])
    baselines = {item["baseline_id"]: item for item in strategy["category_baselines"]}
    covered_baselines: set[str] = set()
    for slot in slots:
        slot["position"] = int(slot.get("position", len(positions) + 1))
        positions.append(slot["position"])
        slot["channel"] = str(slot.get("channel", "listing")).strip()
        slot["task"] = require_text(slot.get("task"), "sequence.slots.task")
        slot["output_method"] = require_text(slot.get("output_method"), "sequence.slots.output_method")
        point_id = str(slot.get("selling_point_id", "")).strip()
        if point_id and point_id not in selling_points:
            raise WorkbenchError(f"sequence references a selling point outside Gate 1: {point_id}")
        slot["selling_point_id"] = point_id
        slot["required_views"] = [str(item).strip() for item in require_list(slot.get("required_views"), "sequence.slots.required_views") if str(item).strip()]
        baseline_ids = [str(item).strip() for item in require_list(slot.get("baseline_ids"), "sequence.slots.baseline_ids") if str(item).strip()]
        if any(item not in baselines for item in baseline_ids):
            raise WorkbenchError("sequence references an unknown category baseline")
        slot["baseline_ids"] = baseline_ids
        covered_baselines.update(baseline_ids)
    if len(positions) != len(set(positions)):
        raise WorkbenchError("sequence positions must be unique")
    missing = [item["baseline_id"] for item in baselines.values() if item["required"] and item["baseline_id"] not in covered_baselines]
    if missing:
        raise WorkbenchError(f"sequence misses required category baselines: {', '.join(missing)}")
    value["slots"] = sorted(slots, key=lambda item: item["position"])
    return value


def validate_contracts(
    intake: dict[str, Any],
    sequence: dict[str, Any],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    contracts = copy.deepcopy(require_list(payload.get("contracts"), "contracts"))
    unique_records(contracts, "slot_key", "contracts")
    sequence_slots = {slot["slot_key"]: slot for slot in sequence["slots"]}
    if set(sequence_slots) != {contract["slot_key"] for contract in contracts}:
        raise WorkbenchError("contracts must cover every approved sequence slot exactly once")
    references = {reference["reference_id"]: reference for reference in intake["references"]}
    claims = {claim["claim_id"]: claim for claim in intake["claims"]}
    product_invariants = [
        f"{fact['label']}: {fact['value']}" for fact in intake["product"]["facts"]
        if fact["required_for_visual"] and fact["status"] == "locked"
    ] + intake["product"]["must_show"]
    global_avoid = intake["product"]["must_not_show"] + intake["brand"]["avoid"]

    normalized = []
    for contract in contracts:
        slot = sequence_slots[contract["slot_key"]]
        contract["operation"] = str(contract.get("operation", "generate"))
        contract["execution_mode"] = str(contract.get("execution_mode", "codex_auto"))
        if contract["operation"] not in {"generate", "edit"}:
            raise WorkbenchError(f"contract {contract['slot_key']} has an invalid operation")
        if contract["execution_mode"] not in {"codex_auto", "manual_import"}:
            raise WorkbenchError(f"contract {contract['slot_key']} has an invalid execution mode")
        contract["prompt"] = require_text(contract.get("prompt"), "contracts.prompt")
        contract["change_only"] = require_text(contract.get("change_only"), "contracts.change_only")
        reference_ids = [str(item).strip() for item in require_list(contract.get("reference_ids"), "contracts.reference_ids") if str(item).strip()]
        if any(item not in references for item in reference_ids):
            raise WorkbenchError(f"contract {contract['slot_key']} references an unknown asset")
        contract["reference_ids"] = reference_ids
        claim_ids = [str(item).strip() for item in require_list(contract.get("claim_ids"), "contracts.claim_ids") if str(item).strip()]
        for claim_id in claim_ids:
            claim = claims.get(claim_id)
            if not claim or claim["status"] not in {"allowed", "qualified"}:
                raise WorkbenchError(f"contract {contract['slot_key']} uses a prohibited or unresolved claim: {claim_id}")
        contract["claim_ids"] = claim_ids
        contract["product_invariants"] = list(dict.fromkeys(product_invariants + [
            str(item).strip() for item in require_list(contract.get("product_invariants"), "contracts.product_invariants") if str(item).strip()
        ]))
        contract["brand_invariants"] = list(dict.fromkeys(intake["brand"]["invariants"] + [
            str(item).strip() for item in require_list(contract.get("brand_invariants"), "contracts.brand_invariants") if str(item).strip()
        ]))
        contract["avoid"] = list(dict.fromkeys(global_avoid + [
            str(item).strip() for item in require_list(contract.get("avoid"), "contracts.avoid") if str(item).strip()
        ]))
        contract["acceptance"] = [
            str(item).strip() for item in require_list(contract.get("acceptance"), "contracts.acceptance") if str(item).strip()
        ]
        if not contract["acceptance"]:
            raise WorkbenchError(f"contract {contract['slot_key']} requires acceptance criteria")
        contract["expected_output"] = contract.get("expected_output") or {"format": "png", "aspect_ratio": "1:1"}
        if not isinstance(contract["expected_output"], dict):
            raise WorkbenchError(f"contract {contract['slot_key']} expected_output must be an object")
        contract["parent_asset_id"] = contract.get("parent_asset_id") or None
        blockers = []
        usable_refs = [references[item] for item in reference_ids if references[item]["approved"] and references[item]["exists"] and references[item]["readable_image"]]
        available_views = {reference["view"] for reference in usable_refs}
        for view in slot["required_views"]:
            if view not in available_views:
                blockers.append(f"missing approved {view} reference")
        if not usable_refs:
            blockers.append("no approved readable reference image")
        if contract["operation"] == "edit" and not contract["parent_asset_id"]:
            blockers.append("edit contract requires parent_asset_id")
        contract["blocked_reasons"] = blockers
        contract["readiness"] = "blocked" if blockers else "ready"
        normalized.append(contract)
    return normalized
