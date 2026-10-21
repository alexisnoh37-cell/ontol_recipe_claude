// 시각화 페이지 진입점: 데이터 로딩, 검색, 층·간선 토글, 노드 정보, 범례, HUD(로딩 시간·fps), 추천 과정 재생 연결.
// 외부 레시피 분석(부록 E)은 adhoc.js가 POST /analyze-recipe 결과를 그래프에 겹쳐 그린다.
// 데이터: GET /graph(기본). ?graph=<url>이면 그 JSON을, ?recipes=all|none이면 그 범위를 불러온다(viz-5 측정용).
// ?display=1이면 표시 전용 레시피(식품안전나라, 엔진 미적재)도 불러온다. 레시피는 출처(origin)별 색·토글(int-2).
// ?layout=tree-ingredient(기본)|tree-cuisine|flat: 나무(주재료 방향·음식 종류) 또는 평면 배치(부록 D-9). 화면에서 바로 바꾼다.
// ?panel=v2: v2(Jev) 추천 과정 탭(부록 H). v2는 레시피 전체가 대상이라 그래프를 recipes=all로 불러온다.

import { GROUP_CATEGORY_LABEL, LAYER_LABEL, LINK_COLOR, LINK_LABEL, NODE_COLOR, ORIGIN_COLOR, PLAY_COLOR, REASON_COLOR, ROLE_LABEL } from "./palette.js";
import { setupAdhoc } from "./adhoc.js";
import { setupBrowse } from "./browse.js";
import { setupPlayback } from "./playback.js";
import { setupPlaybackV2 } from "./playback_v2.js";
import { LAYOUTS, createScene } from "./scene.js";

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const norm = (s) => String(s ?? "").toLowerCase().replace(/\s+/g, "");

const params = new URLSearchParams(location.search);
const t0 = performance.now();
let playback = null;
let playbackV2 = null;
let browse = null;
let originLabels = {};
const withDisplay = ["1", "true"].includes(params.get("display"));
const v2Panel = params.get("panel") === "v2";

async function loadGraph() {
  const scope = encodeURIComponent(params.get("recipes") || (withDisplay || v2Panel ? "all" : "published"));
  const url = params.get("graph") || `/graph?recipes=${scope}${withDisplay ? "&display=true" : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return res.json();
}

// --- 툴팁과 정보 패널 ----------------------------------------------------------------------------

function nodeKindText(n) {
  if (n.kind === "allergen_group") return GROUP_CATEGORY_LABEL[n.category];
  if (n.kind === "recipe") return n.adhoc ? "외부 레시피(분석용, 저장 안 함)" : "레시피";
  if (n.kind === "unmapped") return n.concept ? "분류에만 맞음(미매칭)" : "미매칭 재료(온톨로지에 없음)";
  if (n.is_concept) return "분류(concept)";
  return n.layer === 3 ? (n.is_processed ? "가공품" : "가공품 아님(원천 재료에서 파생)") : "원천 재료";
}

function tooltip(n) {
  const lines = [`<b>${esc(n.name)}</b> <span class="sub">${esc(nodeKindText(n))}</span>`];
  if (n.kind === "recipe" && n.adhoc) {
    lines.push("붙여 넣은 재료로 분석한 임시 노드");
  } else if (n.kind === "unmapped") {
    lines.push(`${n.line_no}번째 줄: ${esc(n.raw_text)}`);
  } else if (n.kind === "recipe") {
    lines.push(`${esc(n.cuisine)} · 난이도 ${n.difficulty ?? "-"} · ${n.cook_time_min ?? "-"}분 · 매운맛 ${n.spicy ?? "-"}`);
    const from = [originLabels[n.origin] || n.origin, n.engine === false ? "추천에 쓰지 않음" : null,
      n.unmapped_lines?.length ? `미매칭 ${n.unmapped_lines.length}/${n.lines}줄` : null].filter(Boolean);
    if (from.length) lines.push(esc(from.join(" · ")));
  } else if (n.kind === "ingredient") {
    const flags = [];
    if (n.is_pantry_staple) flags.push("기본 양념");
    if (n.confidence === "low") flags.push("확신 낮음");
    if (n.layer === 3 && !n.is_processed) flags.push("가공품 아님");
    lines.push([esc(n.category || ""), ...flags].filter(Boolean).join(" · "));
  }
  const extra = (playbackV2?.active ? playbackV2.tooltipExtra(n) : playback?.tooltipExtra(n)) || "";
  return `<div class="tip">${lines.join("<br>")}${extra}</div>`;
}

function chips(items) {
  return items.length ? items.join("") : '<span class="muted">없음</span>';
}

function renderInfo(scene, n) {
  const box = $("#info");
  if (!n) {
    box.innerHTML = '<p class="muted">노드를 클릭하면 연결된 관계만 강조합니다. 빈 곳 클릭 또는 Esc로 해제.</p>';
    return;
  }
  const name = (id) => esc(scene.byId.get(id)?.name ?? id);
  const chip = (id, cls = "") => `<span class="chip ${cls}" data-goto="${esc(id)}">${name(id)}</span>`;
  const inc = scene.incident.get(n.id);
  const out = (type) => inc.filter((l) => l.type === type && l.s === n.id);
  const into = (type) => inc.filter((l) => l.type === type && l.t === n.id);
  const rows = [];
  if (n.kind === "ingredient") {
    rows.push(["층", LAYER_LABEL[n.layer]], ["종류", nodeKindText(n)], ["분류", esc(n.category || "-")]);
    rows.push(["별칭", chips(n.aliases.map((a) => `<span class="chip">${esc(a)}</span>`))]);
    rows.push(["알레르기", n.allergens.length ? n.allergens.map((a) => `<div class="path">${chip(a.group, a.certainty === "possible" ? "possible" : "")
      .replace("</span>", a.certainty === "possible" ? " (포함 가능)</span>" : "</span>")}`
      + `<span class="muted">${a.via.map(name).join(" → ")}</span></div>`).join("") : chips([])]);
    rows.push(["상위(is_a)", chips(out("is_a").map((l) => chip(l.t)))]);
    rows.push(["하위", chips(into("is_a").map((l) => chip(l.s)))]);
    rows.push(["원천", chips(out("derived_from").map((l) => chip(l.t, l.certainty === "possible" ? "possible" : "")))]);
    rows.push(["가공품", chips(into("derived_from").map((l) => chip(l.s)))]);
    rows.push(["쓰는 레시피", `${into("uses").length}개`]);
    if (n.confidence === "low") rows.push(["확신", "낮음(검수표 확인)"]);
  } else if (n.kind === "unmapped") {
    rows.push(["원문", esc(n.raw_text)], ["줄 번호", n.line_no]);
    rows.push(["상태", n.concept ? `분류(concept)에만 맞음: ${chip(n.concept)}<br><span class="muted">더 구체적인 재료로 적어야 합니다</span>`
      : "정규 재료에 없음(별칭·재료 추가는 knowledge 검수로)"]);
    rows.push(["알레르기", "판정하지 못함. 알레르기가 있는 사용자에게는 이 레시피가 제외됩니다"]);
  } else if (n.kind === "recipe") {
    if (n.adhoc) rows.push(["구분", "외부 레시피(일회성 분석, 저장 안 함)"]);
    else {
      rows.push(["출처", esc(originLabels[n.origin] || n.origin || "-")]);
      if (n.engine === false) rows.push(["추천", "쓰지 않음(그래프 표시 전용, 엔진·DB 미적재)"]);
      rows.push(["음식 종류", esc(n.cuisine)], ["난이도", n.difficulty ?? "-"], ["조리시간", n.cook_time_min ? `${n.cook_time_min}분` : "-"], ["매운맛", n.spicy ?? "-"]);
    }
    if (n.required_equipment.length) rows.push(["필수 조리기구", esc(n.required_equipment.join(", "))]);
    // 시판 제품 안내(um-2): 재료 목록 바로 위에, 알레르기 설정과 무관하게 표시
    if (n.commercial_notice) rows.push(["시판 제품", `<div class="commercial-notice">⚠️ ${esc(n.commercial_notice.text)}</div>`
      + chips(n.commercial_notice.ingredients.map((x) => chip(x, "possible")))]);
    for (const role of ["main", "sub", "seasoning", "garnish"]) {
      const ls = out("uses").filter((l) => l.role === role).sort((a, b) => a.line_no - b.line_no);
      if (ls.length) rows.push([ROLE_LABEL[role], chips(ls.map((l) => chip(l.t, l.optional ? "possible" : "")
        .replace("</span>", l.optional ? " (선택)</span>" : "</span>")))]);
    }
    rows.push(["걸리는 알레르기", n.allergens.length ? n.allergens.map((a) => {
      const tags = [a.certainty === "possible" ? "포함 가능" : "포함", ...(a.optional_only ? ["선택 재료 때문"] : [])];
      const hits = a.hits.map((h) => name(h.ingredient) + (h.certainty === "possible" ? "(가능)" : "") + (h.optional ? "(선택)" : ""));
      // 그래프와 같은 기준: 포함(definite)이면서 선택 재료가 아닌 줄이 있으면 진하게, 아니면 흐리게(점선 칩)
      const strong = a.hits.some((h) => h.certainty === "definite" && !h.optional);
      return `<div class="path">${chip(a.group, strong ? "alert" : "possible")}`
        + `<span class="tag">${tags.join(" · ")}</span> <span class="muted">${hits.join(", ")}</span></div>`;
    }).join("") : chips([])]);
    const raws = out("unmapped");
    if (raws.length) {
      rows.push(["미매칭", chips(raws.map((l) => chip(l.t, "alert")))
        + '<br><span class="muted">알레르기를 판정하지 못함(알레르기가 있으면 제외)</span>']);
    } else if (n.has_unmapped) {
      const items = (n.unmapped_lines || []).map((u) => `<span class="chip alert">${esc(u.raw_text)}</span>`);
      rows.push(["미매칭", `${items.length}/${n.lines}줄 ${chips(items)}`
        + '<br><span class="muted">정규 재료에 없음. 알레르기를 판정하지 못함(알레르기가 있으면 제외)</span>']);
    }
    if (n.status !== "published" && !n.adhoc) rows.push(["상태", "검수 전"]);
  } else {
    rows.push(["구분", GROUP_CATEGORY_LABEL[n.category]]);
    if (n.members.length) rows.push(["구성", chips(n.members.map((m) => chip(m)))]);
    const direct = into("allergen");
    if (direct.length) rows.push(["직접 지정 재료", chips(direct.map((l) => chip(l.s, l.certainty === "possible" ? "possible" : "")))]);
    const bundles = into("bundle_member");
    if (bundles.length) rows.push(["포함된 묶음", chips(bundles.map((l) => chip(l.s)))]);
  }
  box.innerHTML = `<h3>${esc(n.name)}</h3><span class="muted">${esc(n.id)}</span>`
    + `<dl>${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;
  for (const el of box.querySelectorAll("[data-goto]")) {
    el.style.cursor = "pointer";
    el.addEventListener("click", () => focusNode(scene, el.dataset.goto));
  }
}

function focusNode(scene, id) {
  if (!scene.byId.has(id)) return;
  scene.select(id);
  scene.flyTo(id);
}

// --- 검색 ----------------------------------------------------------------------------------------

function searchIndex(scene, filter = () => true) {
  return scene.nodes.filter(filter).map((n) => ({
    id: n.id, name: n.name, kind: nodeKindText(n), aliases: n.aliases || [],
    keys: [norm(n.name), ...(n.aliases || []).map(norm)],
  }));
}

// 이름·별칭 정규화(소문자·공백 제거) 후 정확 → 앞부분 → 포함 순, 12개. 방향키·Enter.
function attachSearch(input, list, index, onChoose) {
  let results = [];
  let active = -1;

  function render() {
    list.innerHTML = results.map((r, i) => `<li role="option" data-i="${i}" aria-selected="${i === active}">`
      + `<span>${esc(r.name)}${r.matched ? ` <span class="kind">(${esc(r.matched)})</span>` : ""}</span>`
      + `<span class="kind">${esc(r.kind)}</span></li>`).join("");
    list.hidden = results.length === 0;
  }
  function search(q) {
    const key = norm(q);
    if (!key) { results = []; render(); return; }
    const scored = [];
    for (const e of index) {
      let best = null;
      e.keys.forEach((k, i) => {
        const rank = k === key ? 0 : k.startsWith(key) ? 1 : k.includes(key) ? 2 : null;
        if (rank !== null && (best === null || rank < best.rank)) best = { rank, alias: i > 0 ? e.aliases[i - 1] : null };
      });
      if (best) scored.push({ ...e, rank: best.rank, matched: best.alias });
    }
    scored.sort((a, b) => a.rank - b.rank || a.name.length - b.name.length || a.name.localeCompare(b.name));
    results = scored.slice(0, 12);
    active = results.length ? 0 : -1;
    render();
  }
  function choose(i) {
    const r = results[i];
    if (!r) return;
    results = [];
    render();
    onChoose(r);
  }
  input.addEventListener("input", () => search(input.value));
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && results.length) { active = (active + 1) % results.length; render(); e.preventDefault(); }
    else if (e.key === "ArrowUp" && results.length) { active = (active - 1 + results.length) % results.length; render(); e.preventDefault(); }
    else if (e.key === "Enter") { choose(active); }
    else if (e.key === "Escape") { results = []; render(); }
  });
  list.addEventListener("mousedown", (e) => {
    const li = e.target.closest("li");
    if (li) { e.preventDefault(); choose(Number(li.dataset.i)); }
  });
  input.addEventListener("blur", () => setTimeout(() => { list.hidden = true; }, 100));
}

function setupSearch(scene) {
  const input = $("#search");
  attachSearch(input, $("#search-results"), searchIndex(scene), (r) => {
    input.value = r.name;
    focusNode(scene, r.id);
  });
}

// --- 토글·범례·HUD ------------------------------------------------------------------------------

function setupOrigins(scene, data) {
  originLabels = Object.fromEntries((data.origins || []).map((o) => [o.id, o.label]));
  const box = $("#origin-toggles");
  const display = $("#display-toggle");
  for (const o of data.origins || []) {
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" checked data-origin="${esc(o.id)}"> `
      + `<span class="sw" style="background:${ORIGIN_COLOR[o.id] || NODE_COLOR.recipe}"></span>${esc(o.label)} ${o.recipes}`;
    label.querySelector("input").addEventListener("change", (e) => scene.setOrigin(o.id, e.target.checked));
    box.insertBefore(label, display.closest("label"));
  }
  display.checked = withDisplay;
  display.addEventListener("change", () => {
    const next = new URLSearchParams(location.search);
    if (display.checked) next.set("display", "1"); else next.delete("display");
    location.search = next.toString();
  });
}

function setupLayout(scene) {
  const sel = $("#layout-mode");
  sel.innerHTML = Object.entries(LAYOUTS).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
  sel.value = scene.layout;
  sel.addEventListener("change", () => {
    scene.setLayoutMode(sel.value);
    const next = new URLSearchParams(location.search);
    next.set("layout", sel.value);
    history.replaceState(null, "", `${location.pathname}?${next}`);
  });
}

function setupToggles(scene) {
  for (const el of document.querySelectorAll("[data-layer]")) {
    el.addEventListener("change", () => scene.setLayer(Number(el.dataset.layer), el.checked));
  }
  for (const el of document.querySelectorAll("[data-link]")) {
    el.addEventListener("change", () => scene.setLinkType(el.dataset.link, el.checked));
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !["search", "pantry-add"].includes(document.activeElement?.id)) scene.select(null);
  });
}

function renderLegend() {
  const sw = (color, text, style = "") => `<div class="row"><span class="sw" style="background:${color};${style}"></span>${text}</div>`;
  const ln = (color, text) => `<div class="row"><span class="ln" style="background:${color}"></span>${text}</div>`;
  $("#legend").innerHTML = [
    "<h3>노드</h3>",
    sw(NODE_COLOR.official, "알레르기 그룹: 법정 표시 대상(정육면체)"),
    sw("transparent", "알레르기 그룹: 자체 그룹(테두리)", `border:2px solid ${NODE_COLOR.custom}`),
    sw(NODE_COLOR.bundle, "알레르기 묶음 그룹(팔면체)"),
    sw(NODE_COLOR.raw, "원천 재료(구)", "border-radius:50%"),
    sw("transparent", "분류 concept(와이어프레임)", `border:1px dashed ${NODE_COLOR.concept};border-radius:50%`),
    sw(NODE_COLOR.processed, "가공품(이십면체)"),
    sw(NODE_COLOR.recipe, "레시피(원기둥, 색 = 출처)"),
    ...Object.entries(ORIGIN_COLOR).filter(([k]) => originLabels[k]).map(([k, c]) => sw(c, `　레시피: ${esc(originLabels[k])}`)),
    sw(NODE_COLOR.adhoc, "외부 레시피(분석용, 저장 안 함)"),
    sw("transparent", "외부 레시피의 미매칭 줄(사면체)", `border:1px dashed ${NODE_COLOR.unmapped}`),
    sw("transparent", "확신 낮음(노란 고리)", `border:2px solid ${NODE_COLOR.lowConfidence};border-radius:50%`),
    "<h3>간선</h3>",
    ...Object.entries(LINK_LABEL).map(([k, v]) => ln(LINK_COLOR[k], v)),
    '<div class="row muted">흐린 간선 = 포함 가능(possible) 또는 선택 재료</div>',
    "<h3>재생</h3>",
    sw(PLAY_COLOR.owned, "보유 재료(입력)", "border-radius:50%"),
    sw(PLAY_COLOR.ancestor, "is_a 상속으로 보유 간주", "border-radius:50%"),
    sw(PLAY_COLOR.candidate, "후보 레시피"),
    sw(REASON_COLOR.allergen, "제외: 알레르기(경로를 따라 빛, 가라앉음)"),
    sw(REASON_COLOR.hard_dislike_ingredient, "제외: 절대 불선호 재료"),
    sw(REASON_COLOR.spicy_limit, "제외: 매운맛·조리기구·시간·음식 종류"),
    sw(PLAY_COLOR.rank, "최종 순위(높이 = 점수)"),
    sw(PLAY_COLOR.moved, "다양성 보정으로 자리 이동"),
  ].join("");
}

function startHud(scene, data, loadMs) {
  const hud = $("#hud");
  let frames = 0;
  let last = performance.now();
  let fps = 0;
  const base = `노드 ${data.stats.nodes} · 간선 ${data.stats.links} · 레시피 ${data.stats.recipes} · 로딩 ${(loadMs / 1000).toFixed(2)}초`;
  window.__vizMetrics = { loadMs, fps: 0, nodes: data.stats.nodes, links: data.stats.links };
  function tick(now) {
    frames += 1;
    if (now - last >= 1000) {
      fps = Math.round((frames * 1000) / (now - last));
      frames = 0;
      last = now;
      window.__vizMetrics.fps = fps;
      hud.textContent = `${base} · ${fps} fps`;
    }
    requestAnimationFrame(tick);
  }
  hud.textContent = base;
  requestAnimationFrame(tick);
}

// --- 패널 탭: v1 재생·탐색 / v2(Jev) 추천 과정 ----------------------------------------------------

function setupTabs(data) {
  const allRecipes = params.get("recipes") === "all" || (!params.get("recipes") && (withDisplay || v2Panel));
  function open(tab) {
    for (const b of document.querySelectorAll("[data-tab]")) b.setAttribute("aria-selected", String(b.dataset.tab === tab));
    for (const el of document.querySelectorAll('[data-panel="v1"]')) el.hidden = tab !== "v1";
    $("#v2-card").hidden = tab !== "v2";
    if (tab === "v2") { playback?.stop(); $("#cards-card").hidden = true; } else playbackV2?.stop();
  }
  for (const b of document.querySelectorAll("[data-tab]")) {
    b.addEventListener("click", () => {
      const tab = b.dataset.tab;
      const next = new URLSearchParams(location.search);
      if (tab === "v2") next.set("panel", "v2"); else next.delete("panel");
      if (tab === "v2" && !allRecipes) { // v2는 레시피 전체가 대상: 그래프를 전체로 다시 불러온다
        open("v2");
        $("#v2-status").textContent = `레시피 전체 그래프로 다시 불러오는 중…(지금 ${data.stats.recipes}개)`;
        location.search = next.toString();
        return;
      }
      history.replaceState(null, "", `${location.pathname}?${next}`);
      open(tab);
    });
  }
  open(v2Panel ? "v2" : "v1");
}

// --- 시작 -----------------------------------------------------------------------------------------

async function main() {
  let data;
  try {
    data = await loadGraph();
  } catch (err) {
    $("#loading").textContent = `그래프를 불러오지 못했습니다: ${err.message}`;
    return;
  }
  const tFetched = performance.now();
  const scene = createScene($("#graph"), data, {
    tooltip, onSelect: (n) => { renderInfo(scene, n); browse?.onNodeSelect(n); playbackV2?.onNodeSelect(n); }, layout: params.get("layout") || "tree-ingredient",
  });
  const tScene = performance.now();
  $("#loading").remove();
  setupLayout(scene);
  setupOrigins(scene, data);
  setupSearch(scene);
  setupToggles(scene);
  renderLegend();
  browse = setupBrowse({
    scene, $, attachSearch,
    ingredientIndex: searchIndex(scene, (n) => n.kind === "ingredient" && !n.is_concept),
  });
  playback = setupPlayback({
    scene, $, attachSearch,
    ingredientIndex: searchIndex(scene, (n) => n.kind === "ingredient" && !n.is_concept),
  });
  playbackV2 = setupPlaybackV2({
    scene, $, attachSearch,
    ingredientIndex: searchIndex(scene, (n) => n.kind === "ingredient" && !n.is_concept),
    onActivate: () => playback?.stop(),
  });
  setupTabs(data);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const now = performance.now();
    window.__vizTimings = { fetch: tFetched - t0, scene: tScene - tFetched, firstFrame: now - tScene, ...scene.timings };
    startHud(scene, data, now); // 페이지 이동 시작부터(CDN 모듈 로딩 포함) 첫 화면까지
  }));
  setupAdhoc({ scene, $, esc, select: (id) => focusNode(scene, id) });
  window.__viz = scene; // 디버깅·측정용
}

main();
