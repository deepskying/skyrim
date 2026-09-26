"""Turn the scanned catalogue plus per-category caps into a change list.

Nothing here touches a file: the preview is computed in memory so the GUI can
show exactly what a patch would contain before anything is written.
"""
from __future__ import annotations

LIMITS = {"damage_min": 0, "damage_max": 100, "speed_min": 0.0, "speed_max": 2.0}

DEFAULT_FILTERS = {
    "mod_added_only": True,
    "include_vanilla": False,
    "include_enchanted": False,
    "include_non_playable": False,
    "include_staff": False,
    "include_dummy": False,
}

DEFAULT_OPTIONS = {
    "sync_crit": True,
    "crit_ratio": 0.5,
    "normalize_anim_mult": True,
    "mode": "clamp",
}


def validate_limits(limits: dict | None) -> dict:
    merged = dict(LIMITS)
    for key, value in (limits or {}).items():
        if key in merged and isinstance(value, (int, float)):
            merged[key] = value
    if merged["damage_min"] > merged["damage_max"]:
        merged["damage_min"], merged["damage_max"] = merged["damage_max"], merged["damage_min"]
    if merged["speed_min"] > merged["speed_max"]:
        merged["speed_min"], merged["speed_max"] = merged["speed_max"], merged["speed_min"]
    return merged


def validate_value(kind: str, value, limits: dict) -> tuple[bool, str]:
    """Check one input box value against the configured range."""
    if value is None or value == "":
        return False, "空值"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False, "不是数字"
    low = limits[f"{kind}_min"]
    high = limits[f"{kind}_max"]
    if number < low or number > high:
        return False, f"超出范围 {low}~{high}"
    if kind == "damage" and abs(number - round(number)) > 1e-9:
        return False, "伤害必须是整数"
    return True, ""


def merge_filters(filters: dict | None) -> dict:
    merged = dict(DEFAULT_FILTERS)
    merged.update(filters or {})
    return merged


def merge_options(options: dict | None) -> dict:
    merged = dict(DEFAULT_OPTIONS)
    merged.update(options or {})
    return merged


def is_included(weapon: dict, filters: dict) -> tuple[bool, str]:
    """Decide whether a weapon takes part in this pass, with the reason."""
    if weapon["source"] == "vanilla" and (filters["mod_added_only"] or not filters["include_vanilla"]):
        return False, "原版武器"
    if weapon["non_playable"] and not filters["include_non_playable"]:
        return False, "NPC 专用"
    if weapon["enchanted"] and not filters["include_enchanted"]:
        return False, "附魔副本"
    if weapon["category"] == "staff" and not filters["include_staff"]:
        return False, "法杖"
    if not weapon["damage"] and not filters["include_dummy"]:
        return False, "无伤害记录"
    return True, ""


def _category_peak(weapons: list[dict]) -> dict[str, float]:
    peak: dict[str, float] = {}
    for weapon in weapons:
        if weapon["damage"]:
            peak[weapon["category"]] = max(peak.get(weapon["category"], 0), weapon["damage"])
    return peak


def compute_plan(
    weapons: list[dict],
    caps: dict | None = None,
    overrides: dict | None = None,
    filters: dict | None = None,
    options: dict | None = None,
    limits: dict | None = None,
) -> dict:
    """Return ``{changes, summary, skipped}`` describing the pending patch."""
    filters = merge_filters(filters)
    options = merge_options(options)
    limits = validate_limits(limits)
    caps = caps or {}
    overrides = overrides or {}
    mode = options.get("mode", "clamp")

    included: list[dict] = []
    skipped: dict[str, int] = {}
    excluded = 0
    for weapon in weapons:
        manual = overrides.get(weapon["key"]) or {}
        if manual.get("excluded"):
            excluded += 1
            continue
        keep, reason = is_included(weapon, filters)
        if keep:
            included.append(weapon)
        elif reason:
            skipped[reason] = skipped.get(reason, 0) + 1
    if excluded:
        skipped["手动排除"] = excluded

    peak = _category_peak(included)
    changes: list[dict] = []
    invalid: list[dict] = []

    for weapon in included:
        category = weapon["category"]
        cap = caps.get(category) or {}
        manual = overrides.get(weapon["key"]) or {}
        before = {
            "damage": weapon["damage"],
            "speed": weapon["speed"],
            "crit": weapon["crit"],
            "anim_mult": weapon["anim_mult"],
        }
        after = dict(before)
        reasons: list[str] = []

        if "damage" in manual and manual["damage"] is not None:
            ok, message = validate_value("damage", manual["damage"], limits)
            if not ok:
                invalid.append({"key": weapon["key"], "field": "damage", "message": message})
            else:
                after["damage"] = int(round(float(manual["damage"])))
                reasons.append("manual")
        elif cap.get("damage") is not None and before["damage"]:
            cap_damage = float(cap["damage"])
            if mode == "ratio" and cap_damage < (peak.get(category) or 0):
                factor = cap_damage / peak[category]
                value = max(limits["damage_min"], min(limits["damage_max"], int(round(before["damage"] * factor))))
                if value != before["damage"]:
                    after["damage"] = value
                    reasons.append("cap-ratio")
            elif before["damage"] > cap_damage:
                value = int(round(cap_damage))
                value = max(limits["damage_min"], min(limits["damage_max"], value))
                if value != before["damage"]:
                    after["damage"] = value
                    reasons.append("cap")

        if "speed" in manual and manual["speed"] is not None:
            ok, message = validate_value("speed", manual["speed"], limits)
            if not ok:
                invalid.append({"key": weapon["key"], "field": "speed", "message": message})
            else:
                after["speed"] = round(float(manual["speed"]), 4)
                reasons.append("manual")
        elif cap.get("speed") is not None and before["speed"] is not None:
            if before["speed"] > float(cap["speed"]):
                value = round(float(cap["speed"]), 4)
                value = max(limits["speed_min"], min(limits["speed_max"], value))
                if abs(value - before["speed"]) > 1e-6:
                    after["speed"] = value
                    reasons.append("cap")

        if options.get("sync_crit") and before["crit"] is not None and after["damage"] != before["damage"]:
            ratio = float(options.get("crit_ratio") or 0.5)
            after["crit"] = int(round(after["damage"] * ratio))
            reasons.append("crit")

        if (
            options.get("normalize_anim_mult")
            and before["anim_mult"] is not None
            and abs(before["anim_mult"] - 1.0) > 1e-6
        ):
            after["anim_mult"] = 1.0
            reasons.append("anim-mult")

        if after != before:
            changes.append(
                {
                    "key": weapon["key"],
                    "name": weapon["name"],
                    "edid": weapon["edid"],
                    "category": category,
                    "owner_name": weapon["owner_name"],
                    "mod": weapon.get("mod") or weapon["owner_name"],
                    "winner": weapon["winner"],
                    "before": before,
                    "after": after,
                    "reasons": reasons,
                }
            )

    by_category: dict[str, int] = {}
    for change in changes:
        by_category[change["category"]] = by_category.get(change["category"], 0) + 1

    return {
        "changes": changes,
        "invalid": invalid,
        "skipped": skipped,
        "summary": {
            "included": len(included),
            "changed": len(changes),
            "unchanged": len(included) - len(changes),
            "by_category": by_category,
            "mode": mode,
        },
    }


def plan_to_csv(plan: dict) -> str:
    """Render the change list as CSV for review and diffing."""
    rows = [
        "类别,名称,EditorID,来源插件,最终覆盖插件,原伤害,新伤害,原攻速,新攻速,原暴击,新暴击,原倍率,新倍率,原因"
    ]
    for change in plan["changes"]:
        before, after = change["before"], change["after"]
        rows.append(
            ",".join(
                str(value)
                for value in (
                    change["category"],
                    change["name"].replace(",", "，"),
                    change["edid"],
                    change["owner_name"],
                    change["winner"],
                    before["damage"],
                    after["damage"],
                    before["speed"],
                    after["speed"],
                    before["crit"],
                    after["crit"],
                    before["anim_mult"],
                    after["anim_mult"],
                    "+".join(change["reasons"]),
                )
            )
        )
    return "\n".join(rows) + "\n"
