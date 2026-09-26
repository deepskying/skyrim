/* Weapon balancer UI: tabs per animation type, cap inputs with range checks,
   a searchable weapon list, per-weapon overrides and a change preview. */

const PAGE_SIZE = 200;

const S = {
  limits: { damage_min: 0, damage_max: 100, speed_min: 0, speed_max: 2 },
  caps: {},
  overrides: {},
  filters: {},
  options: { sync_crit: true, crit_ratio: 0.5, normalize_anim_mult: true, mode: "clamp" },
  categories: [],
  vanillaCeiling: {},
  vanillaSpeed: {},
  weapons: [],
  plan: { changes: [], summary: {}, skipped: {}, invalid: [] },
  activeTab: "",
  page: 1,
  detailKey: null,
  onlyChanged: false,
};

const $ = (id) => document.getElementById(id);
const catLabel = (key) => (S.categories.find((c) => c.key === key) || { label: key }).label;
const fmt = (value, digits) => (value === null || value === undefined ? "—" : Number(value).toFixed(digits));
const shortPlugin = (name) => String(name || "").replace(/\.(esp|esm|esl)$/i, "");

function escapeHtml(text) {
  return String(text === null || text === undefined ? "" : text).replace(/[&<>"']/g, (ch) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
  ));
}

async function api(path, body) {
  const options = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : {};
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`${path} -> ${response.status}`);
  return response.json();
}

/* ---------------------------------------------------------------- validation */

function validate(kind, raw) {
  if (raw === "" || raw === null || raw === undefined) return { ok: true, empty: true };
  const number = Number(raw);
  if (Number.isNaN(number)) return { ok: false, message: "不是数字" };
  if (kind === "damage") {
    if (!Number.isInteger(number)) return { ok: false, message: "伤害必须是整数" };
    if (number < S.limits.damage_min || number > S.limits.damage_max) {
      return { ok: false, message: `范围 ${S.limits.damage_min}~${S.limits.damage_max}` };
    }
  } else {
    if (number < S.limits.speed_min || number > S.limits.speed_max) {
      return { ok: false, message: `范围 ${S.limits.speed_min}~${S.limits.speed_max}` };
    }
  }
  return { ok: true, value: number };
}

function bindValidated(input, errorEl, kind) {
  const check = () => {
    const result = validate(kind, input.value);
    input.classList.toggle("invalid", !result.ok);
    errorEl.textContent = result.ok ? "" : result.message;
    return result;
  };
  input.addEventListener("input", check);
  return check;
}

/* -------------------------------------------------------------------- saving */

let saveTimer = null;
function saveState() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    api("/api/state", {
      caps: S.caps,
      overrides: S.overrides,
      filters: S.filters,
      options: S.options,
      limits: S.limits,
    }).catch((error) => console.warn("state save failed", error));
  }, 350);
}

/* --------------------------------------------------------------------- tabs */

function renderTabs() {
  const counts = {};
  const changed = S.plan.summary?.by_category || {};
  const total = {};
  for (const weapon of S.weapons) {
    if (!matchesFilters(weapon, true)) continue;
    total[weapon.category] = (total[weapon.category] || 0) + 1;
  }
  $("tabs").innerHTML = S.categories
    .map((category) => {
      counts[category.key] = total[category.key] || 0;
      const badge = changed[category.key] ? `<span class="badge">${changed[category.key]}</span>` : "";
      const active = category.key === S.activeTab ? " active" : "";
      return `<button class="tab${active}" data-cat="${category.key}">${escapeHtml(category.label)}<span class="count">${counts[category.key]}</span>${badge}</button>`;
    })
    .join("");
  for (const button of document.querySelectorAll(".tab")) {
    button.addEventListener("click", () => {
      S.activeTab = button.dataset.cat;
      S.page = 1;
      S.detailKey = null;
      renderCaps();
      renderTabs();
      renderTable();
    });
  }
}

/* --------------------------------------------------------------- cap inputs */

function renderCaps() {
  const cap = S.caps[S.activeTab] || {};
  $("cap-title").textContent = catLabel(S.activeTab);
  $("cap-hint").textContent = `原版最高伤害 ${S.vanillaCeiling[S.activeTab] ?? "—"} · 原版攻速 ${fmt(S.vanillaSpeed[S.activeTab], 2)}`;
  $("cap-damage").value = cap.damage ?? "";
  $("cap-speed").value = cap.speed ?? "";
  $("cap-mode").value = cap.mode || S.options.mode || "clamp";
  $("cap-damage").dispatchEvent(new Event("input"));
  $("cap-speed").dispatchEvent(new Event("input"));
  updateCapSummary();
}

function updateCapSummary() {
  const rows = S.plan.changes.filter((change) => change.category === S.activeTab);
  const included = S.weapons.filter(
    (weapon) => weapon.category === S.activeTab && matchesFilters(weapon, true)
  ).length;
  $("cap-summary").textContent = included
    ? `本类纳入 ${included} 把，将修改 ${rows.length} 把`
    : "本类没有可处理的武器";
}

async function refreshPlan() {
  try {
    S.plan = await api("/api/plan", {
      caps: S.caps,
      overrides: S.overrides,
      filters: S.filters,
      options: S.options,
      limits: S.limits,
    });
  } catch (error) {
    console.error(error);
    return;
  }
  renderPreview();
  renderTabs();
  renderTable();
  updateCapSummary();
}

/* ------------------------------------------------------------------ filtering */

function matchesFilters(weapon, ignoreSearch) {
  const filters = S.filters;
  if (!filters.include_vanilla && weapon.source === "vanilla") return false;
  if (filters.mod_added_only && weapon.source !== "mod") return false;
  if (!filters.include_enchanted && weapon.enchanted) return false;
  if (!filters.include_non_playable && weapon.non_playable) return false;
  if (!filters.include_staff && weapon.category === "staff") return false;
  if (!filters.include_dummy && !weapon.damage) return false;
  if (!ignoreSearch) {
    const needle = $("search").value.trim().toLowerCase();
    if (needle) {
      const haystack = `${weapon.name} ${weapon.edid} ${weapon.owner_name}`.toLowerCase();
      if (!haystack.includes(needle)) return false;
    }
    if (S.onlyChanged && !changeMap().has(weapon.key)) return false;
  }
  return true;
}

function changeMap() {
  if (!S._changeMap || S._changeMapPlan !== S.plan) {
    S._changeMap = new Map(S.plan.changes.map((change) => [change.key, change]));
    S._changeMapPlan = S.plan;
  }
  return S._changeMap;
}

/* --------------------------------------------------------------------- table */

function weaponBadges(weapon, change) {
  const badges = [];
  const cap = S.caps[weapon.category] || {};
  const excluded = S.overrides[weapon.key]?.excluded;
  if (excluded) badges.push('<span class="badge">已排除</span>');
  if (S.overrides[weapon.key] && !excluded) badges.push('<span class="badge manual">单把设定</span>');
  if (weapon.source === "vanilla") badges.push('<span class="badge">原版</span>');
  if (weapon.enchanted) badges.push('<span class="badge">附魔</span>');
  if (weapon.non_playable) badges.push('<span class="badge">NPC 专用</span>');
  if (cap.damage != null && weapon.damage > cap.damage) badges.push('<span class="badge warn">超上限</span>');
  if (weapon.weight === 0) badges.push('<span class="badge warn">重量 0</span>');
  if (weapon.crit === 0) badges.push('<span class="badge warn">暴击 0</span>');
  if (weapon.anim_mult !== null && Math.abs(weapon.anim_mult - 1) > 1e-6) {
    badges.push('<span class="badge warn">倍率 ' + fmt(weapon.anim_mult, 2) + "</span>");
  }
  if (change) badges.push('<span class="badge ok">将修改</span>');
  return badges.join("");
}

function renderTable() {
  const list = S.weapons
    .filter((weapon) => weapon.category === S.activeTab && matchesFilters(weapon))
    .sort((a, b) => (b.damage || 0) - (a.damage || 0));
  const changes = changeMap();
  const shown = list.slice(0, S.page * PAGE_SIZE);
  const rows = shown
    .map((weapon) => {
      const change = changes.get(weapon.key);
      const newDamage = change ? change.after.damage : weapon.damage;
      const newSpeed = change ? change.after.speed : weapon.speed;
      const damageCell =
        newDamage === weapon.damage
          ? `<span class="newval same">${weapon.damage ?? "—"}</span>`
          : `<span class="newval">${newDamage ?? "—"}</span>`;
      const speedCell =
        newSpeed === weapon.speed
          ? `<span class="newval same">${fmt(weapon.speed, 2)}</span>`
          : `<span class="newval">${fmt(newSpeed, 2)}</span>`;
      const checked = S.overrides[weapon.key]?.excluded ? "" : "checked";
      const detail =
        S.detailKey === weapon.key
          ? `<tr class="detail-row"><td colspan="9">${detailForm(weapon)}</td></tr>`
          : "";
      return `
        <tr class="${change ? "dirty" : ""}" data-key="${weapon.key}">
          <td><input type="checkbox" class="include" data-key="${weapon.key}" ${checked}></td>
          <td class="name-cell">
            <a href="#" class="open-detail label" data-key="${weapon.key}" title="${escapeHtml(weapon.name || weapon.edid)}">${escapeHtml(weapon.name || weapon.edid)}</a>
            <div class="mod-name" title="模组：${escapeHtml(weapon.mod)}｜插件：${escapeHtml(weapon.owner_name)}">${escapeHtml(weapon.mod)}</div>
          </td>
          <td class="edid" title="${escapeHtml(weapon.edid)}">${escapeHtml(weapon.edid)}</td>
          <td class="num">${weapon.damage ?? "—"}</td>
          <td class="num">${damageCell}</td>
          <td class="num">${fmt(weapon.speed, 2)}</td>
          <td class="num">${speedCell}</td>
          <td class="num">${fmt(weapon.weight, 1)}</td>
          <td class="status-cell">${weaponBadges(weapon, change)}</td>
        </tr>${detail}`;
    })
    .join("");
  $("rows").innerHTML = rows || '<tr><td colspan="9" class="hint">没有符合条件的武器</td></tr>';
  $("table-count").textContent = `本类 ${list.length} 把，已显示 ${shown.length} 把`;
  $("load-more").hidden = shown.length >= list.length;
  wireTable();
}

function detailForm(weapon) {
  const manual = S.overrides[weapon.key] || {};
  const error = S.plan.invalid.filter((item) => item.key === weapon.key);
  return `
    <div class="detail-form">
      <label>伤害
        <input type="number" id="d-damage" min="${S.limits.damage_min}" max="${S.limits.damage_max}" step="1"
               value="${manual.damage ?? ""}" placeholder="${weapon.damage ?? ""}">
      </label>
      <label>攻速
        <input type="number" id="d-speed" min="${S.limits.speed_min}" max="${S.limits.speed_max}" step="0.05"
               value="${manual.speed ?? ""}" placeholder="${fmt(weapon.speed, 2)}">
      </label>
      <div class="detail-actions">
        <button class="primary" id="d-apply">应用到这一把</button>
        <button class="ghost" id="d-clear">清除单把设定</button>
      </div>
      <span class="hint">${escapeHtml(error.map((item) => `${item.field}: ${item.message}`).join("；"))}</span>
      <span class="hint">当前：伤害 ${weapon.damage ?? "—"} · 攻速 ${fmt(weapon.speed, 2)} · 暴击 ${weapon.crit ?? "—"} · 重量 ${fmt(weapon.weight, 1)}</span>
      <span class="hint">模组：${escapeHtml(weapon.mod)}｜插件：${escapeHtml(weapon.owner_name)}${weapon.overridden ? `｜最终覆盖：${escapeHtml(weapon.winner_name)}（${escapeHtml(weapon.winner_mod)}）` : ""}</span>
      <span class="hint">关键词：${escapeHtml((weapon.keywords || []).join(" · ") || "无")}</span>
    </div>`;
}

function wireTable() {
  for (const box of document.querySelectorAll(".include")) {
    box.addEventListener("change", () => {
      const key = box.dataset.key;
      const entry = S.overrides[key] || {};
      if (box.checked) delete entry.excluded;
      else entry.excluded = true;
      if (Object.keys(entry).length) S.overrides[key] = entry;
      else delete S.overrides[key];
      saveState();
      refreshPlan();
    });
  }
  for (const link of document.querySelectorAll(".open-detail")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      S.detailKey = S.detailKey === link.dataset.key ? null : link.dataset.key;
      renderTable();
    });
  }
  const damageInput = $("d-damage");
  if (damageInput) {
    const errorEl = document.createElement("span");
    errorEl.className = "field-error";
    damageInput.parentElement.append(errorEl);
    const speedInput = $("d-speed");
    const speedError = document.createElement("span");
    speedError.className = "field-error";
    speedInput.parentElement.append(speedError);
    bindValidated(damageInput, errorEl, "damage");
    bindValidated(speedInput, speedError, "speed");
    $("d-apply").addEventListener("click", () => {
      const damageCheck = validate("damage", damageInput.value);
      const speedCheck = validate("speed", speedInput.value);
      if (!damageCheck.ok || !speedCheck.ok) return;
      const entry = S.overrides[S.detailKey] || {};
      delete entry.excluded;
      if (damageCheck.empty) delete entry.damage;
      else entry.damage = damageCheck.value;
      if (speedCheck.empty) delete entry.speed;
      else entry.speed = speedCheck.value;
      if (Object.keys(entry).length) S.overrides[S.detailKey] = entry;
      else delete S.overrides[S.detailKey];
      saveState();
      refreshPlan();
    });
    $("d-clear").addEventListener("click", () => {
      delete S.overrides[S.detailKey];
      saveState();
      refreshPlan();
    });
  }
}

/* ------------------------------------------------------------------- preview */

function renderPreview() {
  const summary = S.plan.summary || {};
  const skipped = S.plan.skipped || {};
  const skippedText = Object.entries(skipped)
    .filter(([, count]) => count)
    .map(([reason, count]) => `${reason} ${count}`)
    .join(" · ");
  $("preview-summary").innerHTML =
    `纳入 <b>${summary.included ?? 0}</b> 把，将修改 <b>${summary.changed ?? 0}</b> 把` +
    `<div class="hint">跳过：${escapeHtml(skippedText || "无")}</div>`;

  const list = S.plan.changes.slice(0, 200);
  $("preview-list").innerHTML = list
    .map((change) => {
      const parts = [];
      if (change.after.damage !== change.before.damage) {
        parts.push(`伤害 ${change.before.damage} → ${change.after.damage}`);
      }
      if (change.after.speed !== change.before.speed) {
        parts.push(`攻速 ${fmt(change.before.speed, 2)} → ${fmt(change.after.speed, 2)}`);
      }
      if (change.after.crit !== change.before.crit) {
        parts.push(`暴击 ${change.before.crit} → ${change.after.crit}`);
      }
      if (change.after.anim_mult !== change.before.anim_mult) {
        parts.push(`倍率 ${fmt(change.before.anim_mult, 2)} → ${fmt(change.after.anim_mult, 2)}`);
      }
      return `<div class="preview-item">[${escapeHtml(catLabel(change.category))}] <span class="name">${escapeHtml(change.name || change.edid)}</span><br><span class="hint">${escapeHtml(change.mod || change.owner_name)} · ${escapeHtml(parts.join(" · "))}</span></div>`;
    })
    .join("") || '<div class="hint">还没有任何变更</div>';
  if (S.plan.changes.length > list.length) {
    $("preview-list").innerHTML += `<div class="hint">… 其余 ${S.plan.changes.length - list.length} 条见导出的 CSV</div>`;
  }
}

/* --------------------------------------------------------------------- wire */

function wireHeader() {
  $("rescan").addEventListener("click", async () => {
    $("meta").textContent = "正在重新扫描载入顺序…";
    const result = await api("/api/rescan", {});
    applyBootstrap(result);
    S.weapons = (await api("/api/weapons")).weapons;
    renderAll();
  });
  $("suggest-all").addEventListener("click", () => {
    const k = Number($("k-value").value) || 3;
    for (const category of S.categories) {
      const ceiling = S.vanillaCeiling[category.key];
      const speed = S.vanillaSpeed[category.key];
      if (!ceiling) continue;
      const damage = Math.min(S.limits.damage_max, Math.round(ceiling * k));
      const speedCap = Math.min(S.limits.speed_max, Math.round(speed * 1.5 * 100) / 100);
      S.caps[category.key] = { damage, speed: speedCap, mode: S.options.mode };
    }
    saveState();
    renderCaps();
    refreshPlan();
  });
}

function wireCapPanel() {
  const damageCheck = bindValidated($("cap-damage"), $("cap-damage-error"), "damage");
  const speedCheck = bindValidated($("cap-speed"), $("cap-speed-error"), "speed");
  $("apply-cap").addEventListener("click", () => {
    const damage = damageCheck();
    const speed = speedCheck();
    if (!damage.ok || !speed.ok) return;
    const entry = {};
    if (!damage.empty) entry.damage = damage.value;
    if (!speed.empty) entry.speed = speed.value;
    entry.mode = $("cap-mode").value;
    if (Object.keys(entry).length === 1) return;
    S.caps[S.activeTab] = entry;
    saveState();
    refreshPlan();
  });
  $("clear-cap").addEventListener("click", () => {
    delete S.caps[S.activeTab];
    $("cap-damage").value = "";
    $("cap-speed").value = "";
    saveState();
    refreshPlan();
  });
  $("cap-mode").addEventListener("change", () => {
    S.options.mode = $("cap-mode").value;
    if (S.caps[S.activeTab]) S.caps[S.activeTab].mode = S.options.mode;
    saveState();
    refreshPlan();
  });
  $("opt-crit").addEventListener("change", () => {
    S.options.sync_crit = $("opt-crit").checked;
    saveState();
    refreshPlan();
  });
  $("opt-animmult").addEventListener("change", () => {
    S.options.normalize_anim_mult = $("opt-animmult").checked;
    saveState();
    refreshPlan();
  });
  $("load-more").addEventListener("click", () => {
    S.page += 1;
    renderTable();
  });
}

function wireFilters() {
  const mapping = [
    ["f-mod", "mod_added_only"],
    ["f-vanilla", "include_vanilla"],
    ["f-enchanted", "include_enchanted"],
    ["f-nonplayable", "include_non_playable"],
    ["f-staff", "include_staff"],
    ["f-dummy", "include_dummy"],
  ];
  for (const [id, key] of mapping) {
    $(id).addEventListener("change", () => {
      S.filters[key] = $(id).checked;
      // "只看模组新增" and "含原版武器" are two ends of the same switch.
      if (key === "include_vanilla" && $(id).checked) {
        S.filters.mod_added_only = false;
        $("f-mod").checked = false;
      }
      if (key === "mod_added_only" && $(id).checked) {
        S.filters.include_vanilla = false;
        $("f-vanilla").checked = false;
      }
      saveState();
      S.page = 1;
      refreshPlan();
    });
  }
  $("f-changed").addEventListener("change", () => {
    S.onlyChanged = $("f-changed").checked;
    S.page = 1;
    renderTable();
  });
  let timer = null;
  $("search").addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      S.page = 1;
      renderTable();
    }, 150);
  });
  $("refresh-plan").addEventListener("click", refreshPlan);
  $("export-csv").addEventListener("click", async () => {
    $("export-result").textContent = "正在导出…";
    try {
      const result = await api("/api/export", {
        caps: S.caps,
        overrides: S.overrides,
        filters: S.filters,
        options: S.options,
        limits: S.limits,
      });
      $("export-result").textContent = `已导出 ${result.changed} 条变更 → ${result.path}`;
    } catch (error) {
      $("export-result").textContent = `导出失败：${error.message}`;
    }
  });
  $("write-patch").addEventListener("click", async () => {
    const changed = S.plan.summary?.changed ?? 0;
    if (!changed) {
      $("write-result").textContent = "当前没有变更，先生成上限并刷新预览。";
      return;
    }
    const allowed = window.confirm(
      `将在 MO2 的 mods 目录下生成补丁插件：\n\n` +
        `武器平衡-WeaponRebalance\\WeaponRebalance.esp\n\n` +
        `内容：${changed} 条武器记录的覆盖（只改数值）。\n` +
        `不会修改任何原有模组的文件；已存在的补丁会先备份。\n\n继续吗？`
    );
    if (!allowed) return;
    $("write-result").textContent = "正在生成补丁插件…";
    try {
      const report = await api("/api/write", {
        confirm: true,
        caps: S.caps,
        overrides: S.overrides,
        filters: S.filters,
        options: S.options,
        limits: S.limits,
      });
      const verify = report.verify || {};
      $("write-result").innerHTML =
        `已写入 ${report.records} 条记录 → <code>${escapeHtml(report.path)}</code><br>` +
        `master ${report.masters.length} 个 · ESL ${verify.esl ? "是" : "否"} · ` +
        `自检 ${verify.ok ? "通过" : "有问题"}（核对 ${verify.checked} 条）` +
        (report.skipped.length ? `<br>跳过 ${report.skipped.length} 条：${escapeHtml(report.skipped.slice(0, 3).map((item) => `${item.edid}(${item.reason})`).join("、"))}` : "") +
        (verify.problems && verify.problems.length ? `<br>问题：${escapeHtml(verify.problems.slice(0, 3).join("；"))}` : "") +
        `<br>记得在 MO2 里启用它，并放在这批武器模组之后。`;
    } catch (error) {
      $("write-result").textContent = `生成失败：${error.message}`;
    }
  });
}

/* ---------------------------------------------------------------- lifecycle */

function applyBootstrap(data) {
  S.limits = data.limits;
  S.caps = data.caps || {};
  S.overrides = data.overrides || {};
  S.filters = Object.assign(
    {
      mod_added_only: true,
      include_vanilla: false,
      include_enchanted: false,
      include_non_playable: false,
      include_staff: false,
      include_dummy: false,
    },
    data.filters || {}
  );
  S.options = Object.assign(S.options, data.options || {});
  S.categories = data.categories;
  S.vanillaCeiling = data.vanilla_ceiling;
  S.vanillaSpeed = data.vanilla_speed;
  const scan = data.scan || {};
  $("meta").textContent =
    `档案 ${scan.profile} · 插件 ${scan.plugin_count} · 武器记录 ${data.weapon_count} · ` +
    `语言 ${scan.language} · 扫描 ${scan.elapsed}s${scan.from_cache ? "（缓存）" : ""}`;
  $("statusbar").textContent =
    `生成补丁只会写入 MO2\\mods\\武器平衡-WeaponRebalance\\，不会改动任何原有模组文件；` +
    `变更清单导出到 tools/weapon-balancer/output/。` +
    (scan.failures && scan.failures.length ? ` 解析告警 ${scan.failure_count} 个插件。` : "");
  $("f-mod").checked = !!S.filters.mod_added_only;
  $("f-vanilla").checked = !!S.filters.include_vanilla;
  $("f-enchanted").checked = !!S.filters.include_enchanted;
  $("f-nonplayable").checked = !!S.filters.include_non_playable;
  $("f-staff").checked = !!S.filters.include_staff;
  $("f-dummy").checked = !!S.filters.include_dummy;
  $("opt-crit").checked = !!S.options.sync_crit;
  $("opt-animmult").checked = !!S.options.normalize_anim_mult;
  if (!S.activeTab) S.activeTab = S.categories[0].key;
}

function renderAll() {
  renderTabs();
  renderCaps();
  renderTable();
  renderPreview();
  updateCapSummary();
}

async function boot() {
  try {
    applyBootstrap(await api("/api/bootstrap"));
    S.weapons = (await api("/api/weapons")).weapons;
    wireHeader();
    wireCapPanel();
    wireFilters();
    renderAll();
    await refreshPlan();
  } catch (error) {
    $("meta").textContent = `加载失败：${error.message}`;
    console.error(error);
  }
}

document.addEventListener("DOMContentLoaded", boot);
