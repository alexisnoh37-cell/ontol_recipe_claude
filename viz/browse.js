// 재료로 레시피 찾기 (docs/plan.md 6장 "부가 트랙 ui", ui-2). 판정은 하지 않는다: GET /browse 결과를 그리기만 한다.
// 재료는 검색으로 추가하거나, "그래프에서 고르기"를 켜고 재료 노드를 클릭해 추가한다.
// 결과 그래프: 고른 재료(초록) → 조리 가능 레시피(밝은 초록)·거의 가능(노랑)·알레르기 주의(빨강), 모자란 재료(주황).

import { LINK_COLOR, PLAY_COLOR, REASON_COLOR } from "./palette.js";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export const BROWSE_COLOR = { selected: PLAY_COLOR.owned, cookable: "#7ee2a8", near: PLAY_COLOR.candidate, missing: "#ff8b3e", allergy: REASON_COLOR.allergen };

export function setupBrowse({ scene, $, attachSearch, ingredientIndex }) {
  const name = (id) => scene.byId.get(id)?.name ?? String(id).replace(/^[a-z]+:/, "");
  const els = {
    chips: $("#browse-chips"), add: $("#browse-add"), addList: $("#browse-results"), pick: $("#browse-pick"),
    subject: $("#browse-subject"), run: $("#browse-run"), clear: $("#browse-clear"), status: $("#browse-status"),
    list: $("#browse-list"),
  };
  let selected = []; // 정규 재료 id(접두어 없음), 고른 순서
  let shown = false;

  // --- 알레르기 기준(선택) -----------------------------------------------------------------------

  async function loadSubjects() {
    const [personas, profiles] = await Promise.all([
      fetch("/personas").then((r) => (r.ok ? r.json() : [])).catch(() => []),
      fetch("/profiles").then((r) => (r.ok ? r.json() : [])).catch(() => []),
    ]);
    const opt = (value, label, groups) => `<option value="${esc(value)}">${esc(label)}`
      + (groups.length ? ` — 알레르기: ${esc(groups.map((g) => g.name).join(", "))}` : "") + "</option>";
    els.subject.innerHTML = '<option value="">알레르기 표시 안 함</option>'
      + (personas.length ? `<optgroup label="골든셋 페르소나">${personas.map((p) => opt(`persona:${p.id}`, p.name, p.allergen_groups)).join("")}</optgroup>` : "")
      + (profiles.length ? `<optgroup label="저장 프로필">${profiles.map((p) => opt(`profile:${p.id}`, p.display_name, p.allergen_groups)).join("")}</optgroup>` : "");
  }

  // --- 고른 재료 ---------------------------------------------------------------------------------

  function renderChips() {
    els.chips.innerHTML = selected.map((id) => `<span class="chip removable owned" data-goto="ing:${esc(id)}">${esc(name(`ing:${id}`))}`
      + `<button type="button" data-remove="${esc(id)}" aria-label="${esc(name(`ing:${id}`))} 빼기">×</button></span>`).join("")
      || '<span class="muted">재료를 검색하거나 그래프에서 고르세요</span>';
    els.run.disabled = selected.length === 0;
    els.clear.hidden = selected.length === 0 && !shown;
    bindGoto(els.chips);
    for (const b of els.chips.querySelectorAll("[data-remove]")) {
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        selected = selected.filter((x) => x !== b.dataset.remove);
        renderChips();
        if (shown) run();
      });
    }
  }

  function addIngredient(id) {
    if (selected.includes(id)) return;
    selected = [...selected, id];
    renderChips();
    if (shown) run();
  }

  function bindGoto(root) {
    for (const el of root.querySelectorAll("[data-goto]")) {
      el.addEventListener("click", () => {
        if (!scene.byId.has(el.dataset.goto)) return;
        scene.flyTo(el.dataset.goto);
      });
    }
  }

  attachSearch(els.add, els.addList, ingredientIndex, (r) => {
    els.add.value = "";
    addIngredient(r.id.slice(4));
  });

  // --- 실행·결과 ---------------------------------------------------------------------------------

  async function run() {
    if (!selected.length) { clear(); return; }
    const q = new URLSearchParams();
    for (const id of selected) q.append("ingredients", id);
    const [kind, sid] = (els.subject.value || ":").split(":");
    if (kind === "persona") q.set("persona_id", sid);
    if (kind === "profile") q.set("profile_id", sid);
    els.status.textContent = "찾는 중…";
    let res;
    try {
      const r = await fetch(`/browse?${q}`);
      res = await r.json();
      if (!r.ok) throw new Error(typeof res.detail === "string" ? res.detail : r.statusText);
    } catch (err) {
      els.status.textContent = `실패: ${err.message}`;
      return;
    }
    shown = true;
    els.status.textContent = `조리 가능 ${res.cookable.length}개 · 거의 가능 ${res.near.length}개`;
    renderList(res);
    scene.select(null); // 노드 선택 강조가 결과 보기보다 우선하므로 해제한다
    scene.setView(buildView(res));
    renderChips();
  }

  function clear() {
    shown = false;
    els.list.innerHTML = "";
    els.status.textContent = "";
    scene.setView(null);
    renderChips();
  }

  function card(item) {
    const warn = item.allergy_warnings;
    const missing = item.missing.map((m) => `<span class="chip missing">${esc(m.name)}</span>`).join("");
    return `<div class="browse-item${warn.length ? " warn" : ""}" data-goto="${esc(item.graph.recipe)}">`
      + `<div class="title">${warn.length ? "⚠️ " : ""}${esc(item.title)}${item.status !== "published" ? ' <span class="muted">(검수 전)</span>' : ""}</div>`
      + `<div class="muted">${esc(item.cuisine)} · 약 ${esc(item.cook_time_min ?? "-")}분 · 고른 재료 ${item.used.map((u) => esc(u.name)).join(", ")}</div>`
      + (missing ? `<div>더 필요: ${missing}</div>` : "")
      + (warn.length ? `<div class="alert-text">알레르기 주의: ${warn.map((w) => esc(w.text)).join(" / ")}</div>` : "")
      + "</div>";
  }

  function renderList(res) {
    const sec = (title, items, empty) => `<h4>${esc(title)} (${items.length})</h4>`
      + (items.length ? items.map(card).join("") : `<p class="muted">${esc(empty)}</p>`);
    els.list.innerHTML = (res.allergy_notice ? `<p class="notice">${esc(res.allergy_notice)}</p>` : "")
      + sec("바로 만들 수 있는 레시피", res.cookable, "고른 재료만으로 만들 수 있는 레시피가 없습니다.")
      + sec("재료가 조금 모자란 레시피", res.near, "해당하는 레시피가 없습니다.");
    for (const el of els.list.querySelectorAll("[data-goto]")) {
      el.addEventListener("click", () => {
        if (!scene.byId.has(el.dataset.goto)) return;
        scene.flyTo(el.dataset.goto);
      });
    }
  }

  function buildView(res) {
    const nodes = new Map();
    const links = new Map();
    const labels = [];
    for (const s of res.selected) {
      nodes.set(`ing:${s.id}`, { color: BROWSE_COLOR.selected, scale: 1.8 });
      labels.push({ id: `ing:${s.id}`, text: s.name, color: BROWSE_COLOR.selected, px: 13 });
    }
    const draw = (item, color) => {
      const g = item.graph;
      nodes.set(g.recipe, { color: item.allergy_warnings.length ? BROWSE_COLOR.allergy : color, scale: 1.5 });
      labels.push({ id: g.recipe, text: (item.allergy_warnings.length ? "⚠ " : "") + item.title,
        color: item.allergy_warnings.length ? BROWSE_COLOR.allergy : color });
      for (const l of g.owned_links) {
        const link = scene.linkById.get(l);
        if (link) links.set(l, { color: LINK_COLOR[link.role] || color, alpha: 0.9 });
      }
      for (const l of g.missing_links) links.set(l, { color: BROWSE_COLOR.missing, alpha: 0.6 });
      for (const n of g.missing_nodes) if (!nodes.has(n)) nodes.set(n, { color: BROWSE_COLOR.missing, scale: 1.1, opacity: 0.8 });
    };
    for (const item of res.cookable) draw(item, BROWSE_COLOR.cookable);
    for (const item of res.near) draw(item, BROWSE_COLOR.near);
    return { nodes, links, labels };
  }

  els.run.addEventListener("click", run);
  els.clear.addEventListener("click", () => { selected = []; clear(); });
  els.subject.addEventListener("change", () => { if (shown) run(); });

  loadSubjects();
  renderChips();

  return {
    // 그래프에서 고르기가 켜져 있으면 재료 노드 클릭으로 추가한다(분류 concept 노드는 보유 재료가 될 수 없어 제외).
    onNodeSelect(n) {
      if (!els.pick.checked || !n || n.kind !== "ingredient" || n.is_concept) return;
      addIngredient(n.id.slice(4));
      // 고르기 모드의 클릭은 추가만 한다. 결과를 보고 있으면 선택 강조를 풀어 결과 보기를 유지한다
      if (shown) setTimeout(() => scene.select(null), 0);
    },
  };
}
