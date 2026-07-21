from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .p1 import require_list, require_text, resolve_path, unique_records
from .util import WorkbenchError, image_metadata, sha256_file
from .production import normalize_production_spec


FACT_STATUSES = {"locked", "pending", "conflict"}
CLAIM_STATUSES = {"allowed", "qualified", "prohibited", "pending"}
EVIDENCE_STATUSES = {"usable", "directional", "unavailable"}
SOURCE_CLASSES = {"first_party", "external_estimate", "manual"}
ISSUE_AREAS = {"image", "listing", "product", "data", "offer", "traffic"}
LEVELS = {"low", "medium", "high"}
DECISIONS = {"keep", "rollback", "inconclusive"}


def _image_record(record: dict[str, Any], workflow_root: Path | None) -> dict[str, Any]:
    path = resolve_path(record.get("path"), workflow_root)
    record["path"] = str(path) if path else ""
    record["url"] = str(record.get("url", "")).strip()
    record["source"] = str(record.get("source", "manual")).strip()
    record["captured_at"] = str(record.get("captured_at", "")).strip()
    record["exists"] = bool(path and path.is_file())
    record["sha256"] = sha256_file(path) if record["exists"] else None
    if record["exists"]:
        try:
            record["metadata"] = image_metadata(path)
            record["readable_image"] = True
        except WorkbenchError:
            record["metadata"] = {}
            record["readable_image"] = False
    else:
        record["metadata"] = {}
        record["readable_image"] = False
    return record


def _normalize_metrics(metrics: Any, field: str) -> dict[str, float | int | None]:
    if not isinstance(metrics, dict):
        raise WorkbenchError(f"P2 field must be an object: {field}")
    normalized: dict[str, float | int | None] = {}
    for key, raw in metrics.items():
        name = str(key).strip()
        if not name:
            continue
        if raw is None or raw == "":
            normalized[name] = None
            continue
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise WorkbenchError(f"P2 metric must be numeric or null: {field}.{name}")
        normalized[name] = raw
    if not normalized:
        raise WorkbenchError(f"P2 metrics cannot be empty: {field}")
    return normalized


def normalize_optimization_intake(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise WorkbenchError("P2 intake must be a JSON object")
    value = copy.deepcopy(payload)
    schema = value.get("schema_version", "p2-intake.1")
    if schema != "p2-intake.1":
        raise WorkbenchError("schema_version must be p2-intake.1")
    value["schema_version"] = schema

    source = value.setdefault("source", {})
    if not isinstance(source, dict):
        raise WorkbenchError("P2 source must be an object")
    workflow_root = resolve_path(source.get("workflow_root"), None)
    if workflow_root:
        source["workflow_root"] = str(workflow_root)
    source["snapshot_source"] = str(source.get("snapshot_source", "manual")).strip()

    listing = value.setdefault("listing", {})
    if not isinstance(listing, dict):
        raise WorkbenchError("P2 listing must be an object")
    for field in ("asin", "url", "marketplace", "launched_at", "captured_at"):
        listing[field] = require_text(listing.get(field), f"listing.{field}")
    listing["title"] = require_text(listing.get("title"), "listing.title")
    listing["bullets"] = [str(item).strip() for item in require_list(listing.get("bullets"), "listing.bullets") if str(item).strip()]
    listing["description"] = str(listing.get("description", "")).strip()
    listing["image_set_complete"] = bool(listing.get("image_set_complete", False))
    listing["image_set_note"] = str(listing.get("image_set_note", "")).strip()
    images = require_list(listing.get("images"), "listing.images")
    unique_records(images, "slot_key", "listing.images")
    for image in images:
        image["slot_key"] = require_text(image.get("slot_key"), "listing.images.slot_key").upper()
        _image_record(image, workflow_root)
    listing["images"] = images

    product = value.setdefault("product", {})
    if not isinstance(product, dict):
        raise WorkbenchError("P2 product must be an object")
    product["name"] = require_text(product.get("name"), "product.name")
    product["category"] = require_text(product.get("category"), "product.category")
    facts = require_list(product.get("facts"), "product.facts")
    unique_records(facts, "fact_id", "product.facts")
    for fact in facts:
        fact["label"] = require_text(fact.get("label"), "product.facts.label")
        fact["value"] = require_text(fact.get("value"), "product.facts.value")
        fact["status"] = str(fact.get("status", "pending")).strip()
        if fact["status"] not in FACT_STATUSES:
            raise WorkbenchError(f"invalid P2 fact status: {fact['status']}")
        fact["required_for_visual"] = bool(fact.get("required_for_visual", False))
        fact["source"] = str(fact.get("source", "")).strip()
    product["facts"] = facts
    product["must_show"] = [str(item).strip() for item in require_list(product.get("must_show"), "product.must_show") if str(item).strip()]
    product["must_not_show"] = [str(item).strip() for item in require_list(product.get("must_not_show"), "product.must_not_show") if str(item).strip()]

    claims = require_list(value.get("claims"), "claims")
    unique_records(claims, "claim_id", "claims")
    for claim in claims:
        claim["text"] = require_text(claim.get("text"), "claims.text")
        claim["status"] = str(claim.get("status", "pending")).strip()
        if claim["status"] not in CLAIM_STATUSES:
            raise WorkbenchError(f"invalid P2 claim status: {claim['status']}")
        claim["evidence"] = str(claim.get("evidence", "")).strip()
        claim["qualifier"] = str(claim.get("qualifier", "")).strip()
    value["claims"] = claims

    references = require_list(value.get("references"), "references")
    unique_records(references, "reference_id", "references")
    for reference in references:
        reference["role"] = str(reference.get("role", "product")).strip()
        reference["view"] = str(reference.get("view", "detail")).strip()
        reference["approved"] = bool(reference.get("approved", False))
        reference["visible_features"] = [str(item).strip() for item in require_list(reference.get("visible_features"), "references.visible_features") if str(item).strip()]
        _image_record(reference, workflow_root)
    value["references"] = references

    evidence_sources = require_list(value.get("evidence_sources"), "evidence_sources")
    unique_records(evidence_sources, "source_id", "evidence_sources")
    for evidence in evidence_sources:
        evidence["type"] = require_text(evidence.get("type"), "evidence_sources.type")
        evidence["status"] = str(evidence.get("status", "usable")).strip()
        if evidence["status"] not in EVIDENCE_STATUSES:
            raise WorkbenchError(f"invalid evidence status: {evidence['status']}")
        evidence["market"] = str(evidence.get("market", "")).strip()
        evidence["note"] = str(evidence.get("note", "")).strip()
        path = resolve_path(evidence.get("path"), workflow_root)
        evidence["path"] = str(path) if path else ""
        evidence["exists"] = bool(path and path.exists())
    value["evidence_sources"] = evidence_sources

    competitors = require_list(value.get("competitors"), "competitors")
    unique_records(competitors, "competitor_id", "competitors")
    for competitor in competitors:
        competitor["name"] = require_text(competitor.get("name"), "competitors.name")
        competitor["asin_or_url"] = str(competitor.get("asin_or_url", "")).strip()
        listing_path = resolve_path(competitor.get("listing_path"), workflow_root)
        competitor["listing_path"] = str(listing_path) if listing_path else ""
        competitor["listing_exists"] = bool(listing_path and listing_path.is_file())
        image_paths = []
        for raw in require_list(competitor.get("image_paths"), "competitors.image_paths"):
            path = resolve_path(raw, workflow_root)
            image_paths.append({"path": str(path) if path else "", "exists": bool(path and path.is_file())})
        competitor["image_paths"] = image_paths
    value["competitors"] = competitors

    baseline = value.setdefault("baseline", {})
    if not isinstance(baseline, dict):
        raise WorkbenchError("P2 baseline must be an object")
    observations = require_list(baseline.get("observations"), "baseline.observations")
    unique_records(observations, "observation_key", "baseline.observations")
    for observation in observations:
        observation["period_start"] = require_text(observation.get("period_start"), "baseline.observations.period_start")
        observation["period_end"] = require_text(observation.get("period_end"), "baseline.observations.period_end")
        observation["source"] = require_text(observation.get("source"), "baseline.observations.source")
        observation["source_class"] = str(observation.get("source_class", "external_estimate")).strip()
        if observation["source_class"] not in SOURCE_CLASSES:
            raise WorkbenchError(f"invalid observation source_class: {observation['source_class']}")
        observation["phase"] = "before"
        observation["metrics"] = _normalize_metrics(observation.get("metrics"), "baseline.observations.metrics")
        observation["note"] = str(observation.get("note", "")).strip()
    baseline["observations"] = observations
    events = require_list(baseline.get("events"), "baseline.events")
    unique_records(events, "event_key", "baseline.events")
    for event in events:
        event["event_type"] = require_text(event.get("event_type"), "baseline.events.event_type")
        event["started_at"] = require_text(event.get("started_at"), "baseline.events.started_at")
        event["ended_at"] = str(event.get("ended_at", "")).strip()
        event["status"] = str(event.get("status", "open")).strip()
        if event["status"] not in {"open", "resolved"}:
            raise WorkbenchError("baseline event status must be open or resolved")
        event["description"] = require_text(event.get("description"), "baseline.events.description")
        event["source"] = str(event.get("source", "manual")).strip()
    baseline["events"] = events

    requirements = value.setdefault("requirements", {})
    if not isinstance(requirements, dict):
        raise WorkbenchError("P2 requirements must be an object")
    requirements["require_complete_listing_images"] = bool(requirements.get("require_complete_listing_images", True))
    requirements["min_product_references"] = int(requirements.get("min_product_references", 2))
    requirements["min_baseline_periods"] = int(requirements.get("min_baseline_periods", 2))
    if requirements["min_product_references"] < 1 or requirements["min_product_references"] > 20:
        raise WorkbenchError("min_product_references must be between 1 and 20")
    if requirements["min_baseline_periods"] < 1 or requirements["min_baseline_periods"] > 24:
        raise WorkbenchError("min_baseline_periods must be between 1 and 24")
    return value


def build_optimization_readiness(intake: dict[str, Any]) -> dict[str, Any]:
    diagnosis_blockers: list[dict[str, str]] = []
    generation_blockers: list[dict[str, str]] = []
    evaluation_warnings: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    requests: list[dict[str, str]] = []

    locked_facts = [fact for fact in intake["product"]["facts"] if fact["status"] == "locked"]
    if not locked_facts:
        diagnosis_blockers.append({"code": "no_locked_facts", "item": "product.facts", "message": "Lock verified product facts before diagnosing image accuracy."})
    usable_evidence = [item for item in intake["evidence_sources"] if item["status"] in {"usable", "directional"} and (item["exists"] or item["note"])]
    if not usable_evidence and not intake["competitors"]:
        diagnosis_blockers.append({"code": "no_evidence", "item": "evidence_sources", "message": "Add VOC, competitor, or other diagnostic evidence."})
    observations = intake["baseline"]["observations"]
    if len(observations) < intake["requirements"]["min_baseline_periods"]:
        diagnosis_blockers.append({"code": "baseline_shortfall", "item": "baseline.observations", "message": f"Add at least {intake['requirements']['min_baseline_periods']} baseline periods."})

    current_images = intake["listing"]["images"]
    readable_current = [image for image in current_images if image["exists"] and image["readable_image"]]
    if intake["requirements"]["require_complete_listing_images"] and not intake["listing"]["image_set_complete"]:
        generation_blockers.append({"code": "listing_image_set_incomplete", "item": "listing.images", "message": "Capture the complete current Listing image sequence before creating challenge versions."})
        requests.append({"type": "listing-capture", "key": "complete-listing-set", "instruction": "Save MAIN, every secondary image, and current A+ images with slot order and capture date."})
    if not readable_current:
        generation_blockers.append({"code": "no_local_listing_image", "item": "listing.images", "message": "At least one current Listing image must exist locally for controlled comparison."})
        requests.append({"type": "listing-capture", "key": "local-current-image", "instruction": "Download the current Listing image files instead of keeping URL-only references."})

    usable_refs = [reference for reference in intake["references"] if reference["approved"] and reference["exists"] and reference["readable_image"]]
    unique_refs = {reference["sha256"] for reference in usable_refs if reference["sha256"]}
    shortfall = max(0, intake["requirements"]["min_product_references"] - len(unique_refs))
    if shortfall:
        generation_blockers.append({"code": "product_reference_shortfall", "item": "references", "message": f"Add {shortfall} distinct approved product reference image(s)."})
        requests.append({"type": "product-capture", "key": "product-reference-shortfall", "instruction": "Add clear product angles that preserve geometry, materials, controls, and included parts."})

    metric_names = {name for observation in observations for name, value in observation["metrics"].items() if value is not None}
    if not {"sessions", "cvr"}.issubset(metric_names):
        evaluation_warnings.append({"code": "no_first_party_conversion", "item": "baseline.observations", "message": "Sessions/CVR are absent. Sorftime sales/rank trends can support context but not isolate image conversion impact."})
        requests.append({"type": "seller-data", "key": "sessions-cvr", "instruction": "Add Seller Central Sessions and Unit Session Percentage for a clean before/after window when available."})
    if not intake["baseline"]["events"]:
        evaluation_warnings.append({"code": "event_timeline_empty", "item": "baseline.events", "message": "No price, promotion, ad, inventory, review, or competitor event timeline was supplied."})
        requests.append({"type": "event-timeline", "key": "confounders", "instruction": "Record price, coupon, ads, promotion, inventory, review, and competitor changes around image publication."})
    if any(item["status"] == "directional" for item in usable_evidence):
        warnings.append({"code": "directional_evidence", "item": "evidence_sources", "message": "Directional evidence may shape hypotheses but must not be treated as UAE market proof."})

    diagnosis_status = "blocked" if diagnosis_blockers else "passed"
    generation_status = "blocked" if diagnosis_blockers or generation_blockers else "passed"
    status = "blocked" if generation_status == "blocked" else ("warning" if warnings or evaluation_warnings else "passed")
    return {
        "status": status,
        "diagnosis_status": diagnosis_status,
        "generation_status": generation_status,
        "evaluation_status": "warning" if evaluation_warnings else "passed",
        "diagnosis_blockers": diagnosis_blockers,
        "generation_blockers": generation_blockers,
        "evaluation_warnings": evaluation_warnings,
        "warnings": warnings,
        "requests": requests,
        "metrics": {
            "current_listing_images": len(current_images),
            "local_current_images": len(readable_current),
            "product_references": len(unique_refs),
            "baseline_periods": len(observations),
            "evidence_sources": len(usable_evidence),
            "competitors": len(intake["competitors"]),
        },
    }


def validate_diagnosis(intake: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(payload)
    issues = require_list(value.get("issues"), "diagnosis.issues")
    if not issues:
        raise WorkbenchError("P2 diagnosis requires at least one issue")
    unique_records(issues, "issue_id", "diagnosis.issues")
    known_evidence = {
        *[fact["fact_id"] for fact in intake["product"]["facts"]],
        *[claim["claim_id"] for claim in intake["claims"]],
        *[reference["reference_id"] for reference in intake["references"]],
        *[source["source_id"] for source in intake["evidence_sources"]],
        *[competitor["competitor_id"] for competitor in intake["competitors"]],
        *[f"listing:{image['slot_key']}" for image in intake["listing"]["images"]],
        *[observation["observation_key"] for observation in intake["baseline"]["observations"]],
    }
    for issue in issues:
        issue["area"] = str(issue.get("area", "image")).strip()
        if issue["area"] not in ISSUE_AREAS:
            raise WorkbenchError(f"invalid diagnosis area: {issue['area']}")
        issue["severity"] = str(issue.get("severity", "medium")).strip()
        issue["confidence"] = str(issue.get("confidence", "medium")).strip()
        if issue["severity"] not in LEVELS or issue["confidence"] not in LEVELS:
            raise WorkbenchError("diagnosis severity and confidence must be low, medium, or high")
        issue["finding"] = require_text(issue.get("finding"), "diagnosis.issues.finding")
        issue["hypothesis"] = require_text(issue.get("hypothesis"), "diagnosis.issues.hypothesis")
        evidence_refs = [str(item).strip() for item in require_list(issue.get("evidence_refs"), "diagnosis.issues.evidence_refs") if str(item).strip()]
        if not evidence_refs:
            raise WorkbenchError(f"diagnosis issue requires evidence_refs: {issue['issue_id']}")
        unknown = sorted(set(evidence_refs) - known_evidence)
        if unknown:
            raise WorkbenchError(f"diagnosis issue references unknown evidence: {', '.join(unknown)}")
        issue["evidence_refs"] = evidence_refs
        issue["target_metrics"] = [str(item).strip() for item in require_list(issue.get("target_metrics"), "diagnosis.issues.target_metrics") if str(item).strip()]
    issue_ids = {issue["issue_id"] for issue in issues}
    priorities = [str(item).strip() for item in require_list(value.get("priority_issue_ids"), "diagnosis.priority_issue_ids") if str(item).strip()]
    if not priorities or len(priorities) != len(set(priorities)) or any(item not in issue_ids for item in priorities):
        raise WorkbenchError("diagnosis priority_issue_ids must contain unique known issue IDs")
    value["issues"] = issues
    value["priority_issue_ids"] = priorities
    for field in ("non_image_risks", "confounders", "evidence_limitations"):
        value[field] = [str(item).strip() for item in require_list(value.get(field), f"diagnosis.{field}") if str(item).strip()]
    return value


def validate_optimization_contracts(
    intake: dict[str, Any],
    diagnosis: dict[str, Any],
    readiness: dict[str, Any],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    contracts = copy.deepcopy(require_list(payload.get("contracts"), "optimization.contracts"))
    if not contracts:
        raise WorkbenchError("P2 requires at least one optimization contract")
    unique_records(contracts, "challenge_key", "optimization.contracts")
    issues = {issue["issue_id"]: issue for issue in diagnosis["issues"]}
    priority_ids = set(diagnosis["priority_issue_ids"])
    current_images = {f"listing:{image['slot_key']}": image for image in intake["listing"]["images"]}
    product_refs = {reference["reference_id"]: reference for reference in intake["references"]}
    available_refs = {**current_images, **product_refs}
    claims = {claim["claim_id"]: claim for claim in intake["claims"]}
    product_invariants = [
        f"{fact['label']}: {fact['value']}" for fact in intake["product"]["facts"]
        if fact["required_for_visual"] and fact["status"] == "locked"
    ] + intake["product"]["must_show"]
    global_blockers = [item["message"] for item in readiness["generation_blockers"]]

    normalized = []
    for contract in contracts:
        contract["challenge_key"] = require_text(contract.get("challenge_key"), "optimization.contracts.challenge_key")
        issue_id = require_text(contract.get("issue_id"), "optimization.contracts.issue_id")
        if issue_id not in priority_ids or issue_id not in issues:
            raise WorkbenchError(f"optimization contract must target an approved priority issue: {issue_id}")
        contract["issue_id"] = issue_id
        contract["slot_key"] = require_text(contract.get("slot_key"), "optimization.contracts.slot_key").upper()
        contract["baseline_slot_key"] = require_text(contract.get("baseline_slot_key", contract["slot_key"]), "optimization.contracts.baseline_slot_key").upper()
        baseline_ref = f"listing:{contract['baseline_slot_key']}"
        if baseline_ref not in current_images:
            raise WorkbenchError(f"unknown baseline Listing slot: {contract['baseline_slot_key']}")
        contract["execution_mode"] = str(contract.get("execution_mode", "manual_import")).strip()
        contract["operation"] = str(contract.get("operation", "generate")).strip()
        if contract["execution_mode"] not in {"codex_auto", "manual_import"}:
            raise WorkbenchError("optimization execution_mode must be codex_auto or manual_import")
        if contract["operation"] not in {"generate", "edit"}:
            raise WorkbenchError("optimization operation must be generate or edit")
        contract["prompt"] = require_text(contract.get("prompt"), "optimization.contracts.prompt")
        contract["change_only"] = require_text(contract.get("change_only"), "optimization.contracts.change_only")
        contract["parent_asset_id"] = contract.get("parent_asset_id") or None
        reference_ids = [str(item).strip() for item in require_list(contract.get("reference_ids"), "optimization.contracts.reference_ids") if str(item).strip()]
        if baseline_ref not in reference_ids:
            reference_ids.insert(0, baseline_ref)
        unknown = sorted(set(reference_ids) - set(available_refs))
        if unknown:
            raise WorkbenchError(f"optimization contract references unknown images: {', '.join(unknown)}")
        contract["reference_ids"] = reference_ids
        claim_ids = [str(item).strip() for item in require_list(contract.get("claim_ids"), "optimization.contracts.claim_ids") if str(item).strip()]
        for claim_id in claim_ids:
            claim = claims.get(claim_id)
            if not claim or claim["status"] not in {"allowed", "qualified"} or not claim["evidence"]:
                raise WorkbenchError(f"optimization contract uses an unresolved claim: {claim_id}")
        contract["claim_ids"] = claim_ids
        contract["product_invariants"] = list(dict.fromkeys(product_invariants + [str(item).strip() for item in require_list(contract.get("product_invariants"), "optimization.contracts.product_invariants") if str(item).strip()]))
        contract["avoid"] = list(dict.fromkeys(intake["product"]["must_not_show"] + [str(item).strip() for item in require_list(contract.get("avoid"), "optimization.contracts.avoid") if str(item).strip()]))
        contract["acceptance"] = [str(item).strip() for item in require_list(contract.get("acceptance"), "optimization.contracts.acceptance") if str(item).strip()]
        if not contract["acceptance"]:
            raise WorkbenchError("optimization contract requires acceptance criteria")
        contract["target_metrics"] = [str(item).strip() for item in require_list(contract.get("target_metrics", issues[issue_id]["target_metrics"]), "optimization.contracts.target_metrics") if str(item).strip()]
        contract["observation_days"] = int(contract.get("observation_days", 14))
        if contract["observation_days"] < 3 or contract["observation_days"] > 60:
            raise WorkbenchError("observation_days must be between 3 and 60")
        contract["expected_output"] = contract.get("expected_output") or {"format": "png", "aspect_ratio": "1:1"}
        blockers = list(global_blockers)
        for reference_id in reference_ids:
            reference = available_refs[reference_id]
            if not reference["exists"] or not reference["readable_image"]:
                blockers.append(f"reference is not a readable local image: {reference_id}")
        if contract["operation"] == "edit" and not contract["parent_asset_id"]:
            blockers.append("edit contract requires a workbench parent_asset_id")
        production = normalize_production_spec(
            contract.get("production"),
            product_refs,
            [reference_id for reference_id in reference_ids if reference_id in product_refs],
            [str(contract.get("production", {}).get("target_view", "")).strip()] if contract.get("production", {}).get("target_view") else [],
            bool(contract.get("production", {}).get("scene_required", False)),
        )
        if production["route"] in {"deterministic", "composite"} and contract["execution_mode"] != "manual_import":
            production["blockers"].append("locked-product routes require manual_import execution mode")
            production["route"] = "blocked"
        if production["route"] == "concept_only":
            production["blockers"].append("concept-only output is not eligible for direct Listing/A+ release")
            production["route"] = "blocked"
        contract["production"] = production
        blockers.extend(production["blockers"])
        contract["blocked_reasons"] = list(dict.fromkeys(blockers))
        contract["readiness"] = "blocked" if blockers else "ready"
        normalized.append(contract)
    return normalized


def normalize_observation(payload: dict[str, Any], phase: str = "after") -> dict[str, Any]:
    value = copy.deepcopy(payload)
    value["period_start"] = require_text(value.get("period_start"), "observation.period_start")
    value["period_end"] = require_text(value.get("period_end"), "observation.period_end")
    value["source"] = require_text(value.get("source"), "observation.source")
    value["source_class"] = str(value.get("source_class", "manual")).strip()
    if value["source_class"] not in SOURCE_CLASSES:
        raise WorkbenchError("observation source_class must be first_party, external_estimate, or manual")
    value["phase"] = phase
    value["metrics"] = _normalize_metrics(value.get("metrics"), "observation.metrics")
    value["note"] = str(value.get("note", "")).strip()
    return value


def normalize_interference_event(payload: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(payload)
    value["event_type"] = require_text(value.get("event_type"), "event.event_type")
    value["started_at"] = require_text(value.get("started_at"), "event.started_at")
    value["ended_at"] = str(value.get("ended_at", "")).strip()
    value["status"] = str(value.get("status", "open")).strip()
    if value["status"] not in {"open", "resolved"}:
        raise WorkbenchError("event status must be open or resolved")
    value["description"] = require_text(value.get("description"), "event.description")
    value["source"] = str(value.get("source", "manual")).strip()
    return value


def validate_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(payload)
    value["decision"] = str(value.get("decision", "inconclusive")).strip()
    if value["decision"] not in DECISIONS:
        raise WorkbenchError("evaluation decision must be keep, rollback, or inconclusive")
    value["rationale"] = require_text(value.get("rationale"), "evaluation.rationale")
    return value
