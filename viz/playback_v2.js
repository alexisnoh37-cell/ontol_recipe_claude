// v2(Jev) 추천 6단계 재생(docs/plan.md 부록 H-4). 화면은 판정하지 않는다: POST /v2/recommend(trace: true)가
// 돌려준 값만 색·높이·라벨·표로 바꾼다. 3D 그래프와 패널은 같은 단계에서 함께 바뀌고, 패널 행 ↔ 노드가 서로 연결된다.
//   1 못 먹는 것(규칙) → 2 요청 해석(규칙) → 3 제외(규칙) → 4 Jev에 보낸 후보 → 5 순위 판단(Jev 또는 규칙) → 6 결과
// 무대(부록 H-7): 제외된 잎은 땅으로 떨어지고, 후보는 수관 위 순위 무대로 떠올라 점수만큼 높이 서며, 결과는 단상에 오른다.
// 아래 깔때기 막대가 남은 레시피 수를, 카메라는 단계마다 뿌리 → 수관 → 땅 → 무대 순으로 따라간다.

import { LINK_COLOR, PLAY_COLOR, REASON_COLOR, REASON_SHORT } from "./palette.js";

const STEP_TITLES = ["못 먹는 것 (규칙)", "요청 해석 (규칙)", "제외 (규칙)", "Jev에 보낸 후보", "순위 판단", "결과"];
const usedJev = (t) => t.ranking === "jev" || t.jev_failed;
const MODE_LABEL = { random: "🎲 랜덤 추천", pantry: "🥕 내 재료로 추천", dish: "🔎 요리 찾기" };
const AUTO_MS = 5500;
const MOVE_MS = 1400; // 단계 전환 이동 시간
const STAGGER_MS = 1600; // 떨어지고 떠오르는 순서를 보이도록 나눠 주는 최대 지연
const PODIUM_RISE = 320; // 순위 무대에서 점수 1.0일 때 높이
const LABELS = 15;
// 꽃잎 색(항목별, 부록 H-8). Jev 항목과 규칙 점수 항목. 판정과 무관한 표시 색
const PETAL_COLOR = {
  request: "#ffb224", taste: "#ff6b5a", ingredients: "#5fd18b", cuisine: "#58a6ff", skill: "#c49bff", pantry: "#3ccfcf",
  I: "#3ccfcf", K: "#58a6ff", T: "#ff6b5a", P: "#5fd18b", D: "#c49bff", M: "#9aa1ad", S: "#ffb224",
};
const COLOR = { screened: "#c9a0ff", ready: "#7ee2a8", near: "#ffe08a", hardDislike: REASON_COLOR.hard_dislike_ingredient };

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const f2 = (x) => (x == null ? "-" : Number(x).toFixed(2));

export function setupPlaybackV2({ scene, $, attachSearch, ingredientIndex, onActivate }) {
  const name = (id) => scene.byId.get(id)?.name ?? String(id).replace(/^[a-z]+:/, "");
  const els = {
    persona: $("#v2-persona"), info: $("#v2-persona-info"), ranking: $("#v2-ranking"), rankingNote: $("#v2-ranking-note"),
    pantry: $("#v2-pantry-chips"), add: $("#v2-pantry-add"), addList: $("#v2-pantry-results"), pick: $("#v2-pick"),
    query: $("#v2-query"), status: $("#v2-status"), player: $("#v2-player"), dots: $("#v2-dots"),
    prev: $("#v2-prev"), next: $("#v2-next"), auto: $("#v2-auto"), stop: $("#v2-stop"),
    title: $("#v2-step-title"), body: $("#v2-step-body"), cards: $("#v2-cards"),
    funnel: $("#v2-funnel"), autoplay: $("#v2-autoplay"), follow: $("#v2-follow"),
  };
  const personas = new Map();
  let persona = null;
  let pantry = [];
  let run = null; // { response, t, step, filter, mode, byRecipe, ranked, rankOf }
  let timer = null;
  let jevAvailable = false;

  // --- 페르소나·입력 -------------------------------------------------------------------------------

  async function load() {
    const [list, info] = await Promise.all([
      fetch("/v2/personas").then((r) => (r.ok ? r.json() : [])).catch(() => []),
      fetch("/v2/info").then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
    ]);
    for (const p of list) personas.set(p.id, p);
    els.persona.innerHTML = list.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("")
      || '<option value="">페르소나 없음(v2 서버로 실행했는지 확인)</option>';
    jevAvailable = Boolean(info.jev_available);
    els.ranking.innerHTML = `<option value="jev">Jev가 순위 판단${jevAvailable ? "" : " (키 없음 → 규칙으로 대체)"}</option>`
      + '<option value="rules">규칙 점수</option>';
    renderRankingNote();
    choose(els.persona.value);
  }

  function choose(id) {
    stop();
    persona = personas.get(id) || null;
    pantry = persona ? persona.try_pantry.map((x) => x.id) : [];
    if (persona?.try_dish?.length && !els.query.dataset.touched) els.query.value = persona.try_dish[0];
    render();
  }

  function render() {
    if (!persona) { els.info.innerHTML = ""; els.pantry.innerHTML = ""; return; }
    const p = persona;
    const chipsOf = (xs, cls, pre) => xs.length ? xs.map((x) => `<span class="chip ${cls}" data-goto="${pre}${esc(x.id)}">${esc(x.name)}</span>`).join("") : '<span class="muted">없음</span>';
    els.info.innerHTML = (p.description ? `<p class="desc">${esc(p.description)}</p>` : "")
      + `<dl><dt>알레르기</dt><dd>${chipsOf(p.allergens, "alert", "ag:")}</dd>`
      + `<dt>절대 안 먹음</dt><dd>${chipsOf(p.never_eat, "alert", "ing:")}</dd>`
      + `<dt>좋아함</dt><dd>${chipsOf(p.likes, "owned", "ing:")}</dd>`
      + `<dt>싫어함</dt><dd>${chipsOf(p.dislikes, "missing", "ing:")}</dd>`
      + `<dt>매운맛</dt><dd>${p.spicy_level ?? "모름"}${p.spicy_level === 5 ? " (한도 없음)" : ""}</dd>`
      + `<dt>음식 종류</dt><dd>${esc([...p.cuisine_likes.map((c) => `+${c}`), ...p.cuisine_dislikes.map((c) => `−${c}`)].join(" ") || "없음")}</dd>`
      + `<dt>요리 실력</dt><dd>${p.skill_level ?? "모름"}</dd></dl>`;
    els.pantry.innerHTML = pantry.map((id) => `<span class="chip removable owned" data-goto="ing:${esc(id)}">${esc(name(`ing:${id}`))}`
      + `<button type="button" data-remove="${esc(id)}" aria-label="${esc(name(`ing:${id}`))} 빼기">×</button></span>`).join("")
      || '<span class="muted">가진 재료 없음</span>';
    bindGoto(els.info);
    bindGoto(els.pantry);
    for (const b of els.pantry.querySelectorAll("[data-remove]")) {
      b.addEventListener("click", (e) => { e.stopPropagation(); pantry = pantry.filter((x) => x !== b.dataset.remove); render(); });
    }
  }

  function renderRankingNote() {
    els.rankingNote.textContent = els.ranking.value === "jev"
      ? (jevAvailable ? "실제 Jev를 호출합니다(요청당 0.2~1.3초, 입력 약 3만 토큰)." : "Jev 키가 없어 규칙 점수로 대체됩니다(그 사실이 재생에 표시됩니다).")
      : "Jev를 부르지 않고 규칙 점수로 순위를 정합니다.";
  }

  function addPantry(id) {
    if (!pantry.includes(id)) pantry = [...pantry, id].sort();
    render();
  }

  attachSearch(els.add, els.addList, ingredientIndex, (r) => { els.add.value = ""; addPantry(r.id.slice(4)); });
  els.persona.addEventListener("change", () => choose(els.persona.value));
  els.ranking.addEventListener("change", renderRankingNote);
  els.query.addEventListener("input", () => { els.query.dataset.touched = "1"; });
  els.query.addEventListener("keydown", (e) => { if (e.key === "Enter") start("dish"); });
  for (const b of document.querySelectorAll("[data-v2-run]")) b.addEventListener("click", () => start(b.dataset.v2Run));
  for (const b of document.querySelectorAll("[data-v2-example]")) {
    b.addEventListener("click", () => { els.query.value = b.dataset.v2Example; els.query.dataset.touched = "1"; start("dish"); });
  }

  function bindGoto(root) {
    for (const el of root.querySelectorAll("[data-goto]")) {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = el.dataset.goto;
        if (!scene.byId.has(id)) return;
        scene.flyTo(id);
        if (run && el.dataset.filter === undefined) highlightRow(id);
      });
    }
  }

  // --- 실행 ---------------------------------------------------------------------------------------

  async function start(mode) {
    if (!persona) return;
    const query = els.query.value.trim();
    if (mode === "dish" && !query) { els.status.textContent = "찾을 요리를 입력하세요."; return; }
    if (mode === "pantry" && !pantry.length) { els.status.textContent = "가진 재료를 하나 이상 고르세요."; return; }
    onActivate?.();
    const body = { persona_id: persona.id, mode, trace: true, rerank: els.ranking.value === "jev" };
    if (mode === "pantry") body.pantry = pantry;
    if (mode === "dish") body.query = query;
    els.status.textContent = `${MODE_LABEL[mode]} 계산 중…${body.rerank && jevAvailable ? " (Jev 판단 대기)" : ""}`;
    for (const b of document.querySelectorAll("[data-v2-run]")) b.disabled = true;
    const t0 = performance.now();
    try {
      const res = await fetch("/v2/recommend", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const json = await res.json();
      if (!res.ok) throw new Error(typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail));
      const t = json.trace;
      const byRecipe = new Map();
      for (const e of t.exclusions) {
        if (!byRecipe.has(e.recipe)) byRecipe.set(e.recipe, []);
        byRecipe.get(e.recipe).push(e);
      }
      run = { response: json, t, mode, step: 0, filter: null, byRecipe, ms: performance.now() - t0,
        rankOf: new Map(t.ranked.map((r) => [r.recipe, r])), groupOf: groupIndex(t) };
      els.status.textContent = `${MODE_LABEL[mode]} · ${(run.ms / 1000).toFixed(1)}초 · 순위: ${t.ranking === "jev" ? `Jev(${t.model})` : "규칙 점수"}`
        + (t.jev_failed ? " · Jev 실패 → 규칙" : "");
      els.player.hidden = false;
      scene.select(null);
      show(0);
      els.player.scrollIntoView({ block: "start", behavior: "smooth" });
      scene.setStage(true);
      if (els.autoplay.checked) startAuto();
      window.__vizV2 = { get step() { return run?.step; }, get trace() { return run?.t; }, get response() { return run?.response; } };
    } catch (err) {
      els.status.textContent = `실패: ${err.message}`;
    } finally {
      for (const b of document.querySelectorAll("[data-v2-run]")) b.disabled = false;
    }
  }

  function groupIndex(t) {
    const out = new Map();
    for (const [g, ids] of Object.entries(t.groups || {})) for (const id of ids) out.set(id, g);
    return out;
  }

  function stop() {
    pause();
    if (!run) return;
    run = null;
    els.player.hidden = true;
    els.cards.innerHTML = "";
    scene.setView(null);
    scene.setGlyphs([]);
    scene.setTargets(new Map());
    scene.setStage(false);
    els.funnel.hidden = true;
  }

  function pause() {
    if (timer) clearInterval(timer);
    timer = null;
    els.auto.textContent = "▶ 자동재생";
  }

  function stepTitles() {
    const jev = usedJev(run.t);
    return STEP_TITLES.map((s, i) => (i === 3 && !jev ? "순위를 정할 후보" : i === 4 ? `순위 판단 (${run.t.ranking === "jev" ? "Jev" : "규칙"})` : s));
  }

  function show(step, { filter = null } = {}) {
    if (!run) return;
    run.step = Math.max(0, Math.min(5, step));
    run.filter = filter;
    const built = STEPS[run.step]();
    els.dots.innerHTML = stepTitles().map((s, i) => `<button type="button" data-step="${i}" class="${i === run.step ? "on" : ""}" title="${esc(s)}">${i + 1}</button>`).join("");
    for (const b of els.dots.querySelectorAll("[data-step]")) b.addEventListener("click", () => { pause(); show(Number(b.dataset.step)); });
    els.title.textContent = `${run.step + 1}/6 ${stepTitles()[run.step]}`;
    els.body.innerHTML = built.html;
    bindGoto(els.body);
    for (const el of els.body.querySelectorAll("[data-filter]")) {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        pause();
        show(run.step, { filter: run.filter === el.dataset.filter ? null : el.dataset.filter });
      });
    }
    els.prev.disabled = run.step === 0;
    els.next.disabled = run.step === 5;
    els.cards.innerHTML = run.step === 5 ? cardsHtml() : "";
    bindGoto(els.cards);
    scene.setView(built.view);
    scene.setTargets(targetsFor(run.step), MOVE_MS);
    scene.setGlyphs(glyphsFor(run.step));
    renderFunnel();
    if (els.follow.checked) followCamera(run.step);
  }

  els.prev.addEventListener("click", () => { pause(); show(run.step - 1); });
  els.next.addEventListener("click", () => { pause(); show(run.step + 1); });
  els.stop.addEventListener("click", stop);
  function startAuto() {
    if (!run) return;
    if (run.step === 5) show(0);
    els.auto.textContent = "❚❚ 멈춤";
    timer = setInterval(() => { if (!run || run.step >= 5) { pause(); return; } show(run.step + 1); }, AUTO_MS);
  }
  els.auto.addEventListener("click", () => {
    if (!run) return;
    if (timer) { pause(); return; }
    startAuto();
  });

  // --- 무대: 단계별 목표 위치(판정 없이 trace 값만 자리로 바꾼다) -------------------------------------

  const hash01 = (str) => {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) h = Math.imul(h ^ str.charCodeAt(i), 16777619);
    return ((h >>> 0) % 1000) / 1000;
  };
  const stagger = (i, n) => (n > 1 ? (STAGGER_MS * i) / (n - 1) : 0);
  const ringAt = (i, n, r, y, phase = 0) => {
    const a = Math.PI / 2 + phase + (2 * Math.PI * i) / Math.max(1, n);
    return { x: r * Math.cos(a), y, z: r * Math.sin(a) };
  };

  function targetsFor(step) {
    const t = run.t;
    const info = scene.stageInfo();
    const out = new Map();
    if (step === 1 && run.mode === "dish") { // 요청 해석: 비슷한 레시피가 S만큼 제자리에서 솟는다
      for (const sm of t.similarity) {
        const h = scene.homeOf(sm.recipe);
        if (h) out.set(sm.recipe, { ...h, y: h.y + sm.S * 160 });
      }
    }
    if (step >= 2) { // 제외: 확인한 순서대로 잎이 땅으로 떨어진다(자기 방향 그대로, 반지름만 흩뿌림)
      const order = new Map(t.checked.map((c, i) => [c.recipe, i]));
      for (const r of Object.keys(t.excluded)) {
        const h = scene.homeOf(r);
        if (!h) continue;
        const a = Math.atan2(h.z, h.x);
        const rr = info.groundR * (0.3 + 0.62 * hash01(r));
        out.set(r, { x: rr * Math.cos(a), y: info.groundY + 4, z: rr * Math.sin(a),
          delay: step === 2 ? stagger(order.get(r) ?? 0, t.checked.length) : 0 });
      }
    }
    const ready = new Set(t.groups.ready || []);
    const radius = (r) => (ready.has(r) ? info.innerR : info.ringR);
    if (step === 3) { // 후보: 순위 무대 고리로 떠오른다(내 재료로는 지금 바로 = 안쪽 고리)
      const inner = t.pool.filter((r) => ready.has(r));
      const outer = t.pool.filter((r) => !ready.has(r));
      for (const [list, r] of [[inner, info.innerR], [outer, info.ringR]]) {
        list.forEach((id, i) => out.set(id, { ...ringAt(i, list.length, r, info.podiumY), delay: stagger(i, list.length) }));
      }
    }
    if (step >= 4) { // 순위: 순위 순서로 고리를 돌며 점수만큼 높이 선다. 결과는 단상으로
      const shown = t.ranked.filter((x) => x.shown);
      const scores = t.ranked.map((x) => x.score);
      const lo = Math.min(...scores);
      const span = Math.max(...scores) - lo || 1;
      const height = (x) => info.podiumY + 30 + ((x.score - lo) / span) * PODIUM_RISE; // 후보들 안에서의 상대 점수
      t.ranked.forEach((x, i) => {
        if (step === 5 && x.shown) return;
        out.set(x.recipe, { ...ringAt(i, t.ranked.length, radius(x.recipe), height(x)),
          delay: step === 4 ? stagger(i, t.ranked.length) / 2 : 0 });
      });
      if (step === 5) {
        shown.forEach((x, i) => out.set(x.recipe, {
          ...ringAt(i, shown.length, shown.length > 1 ? info.daisR : 0, info.daisY + (shown.length - i) * 14),
          delay: i * 120 }));
      }
    }
    return out;
  }

  // --- 꽃: 순위 단계(5)는 후보 전부, 결과 단계(6)는 결과만. 꽃잎 = 항목, 길이 = 점수, 진하기 = 확신도 -----------

  function petalKeys() {
    const t = run.t;
    if (t.ranking === "jev") return t.jev.aspects;
    return Object.keys(t.ranked[0]?.breakdown || {}).filter((k) => !k.startsWith("J"));
  }

  function glyphsFor(step) {
    const t = run.t;
    if (step < 4 || !t.ranked.length) return [];
    const keys = petalKeys();
    const list = step === 5 ? t.ranked.filter((x) => x.shown) : t.ranked;
    return list.map((x) => ({
      id: x.recipe,
      petals: keys.map((k) => {
        if (t.ranking === "jev") {
          const ans = t.jev.answers[x.recipe]?.[k];
          return { color: PETAL_COLOR[k] || "#e6e8ec", length: ans?.score ?? 0, opacity: ans ? 0.25 + 0.75 * ans.confidence : 0.12 };
        }
        return { color: PETAL_COLOR[k] || "#e6e8ec", length: x.breakdown[k] ?? 0, opacity: 0.85 };
      }),
    }));
  }

  function petalLegend() {
    const t = run.t;
    const ak = L().aspect_ko || {};
    const keys = petalKeys();
    if (!keys.length) return "";
    const name = (k) => (t.ranking === "jev" ? ak[k] || k : `${k} ${t.breakdown_labels[k] || ""}`);
    return `<div class="petal-legend"><span class="muted">꽃잎(12시부터 시계 방향) · 길이 = 점수${t.ranking === "jev" ? " · 진하기 = 확신도" : ""}:</span>`
      + keys.map((k) => `<span><i style="background:${PETAL_COLOR[k] || "#e6e8ec"}"></i>${esc(name(k))}</span>`).join("") + "</div>";
  }

  function followCamera(step) {
    const info = scene.stageInfo();
    const mid = (info.groundY + info.podiumY) / 2;
    const shots = [
      [info.groundY - 120, 1900, 6], // 뿌리(알레르기)
      [info.podiumY - 560, 2500, 16], // 수관(요청 해석)
      [mid, 3600, 9], // 땅까지 한눈에(제외)
      [info.podiumY + 80, 2300, 24], // 순위 무대(후보)
      [info.podiumY + 160, 2200, 20], // 순위 무대(순위)
      [info.daisY - 40, 1500, 26], // 단상(결과)
    ];
    const [y, d, pitch] = shots[step];
    scene.lookAt(y, d, pitch, 1500);
  }

  // --- 깔때기 막대: 전체 → 확인 → 통과 → 후보 → 결과(지금 단계 칸이 밝다) ----------------------------

  let shownCounts = new Map();
  function renderFunnel() {
    const t = run.t;
    const total = scene.nodes.filter((n) => n.kind === "recipe" && n.engine !== false).length;
    const excluded = Object.keys(t.excluded).length;
    const cells = [
      { key: "all", label: "전체", n: total, on: [0, 1] },
      { key: "checked", label: "확인", n: t.checked.length, on: [1, 2] },
      { key: "passed", label: `통과 (제외 ${excluded})`, n: t.checked.length - excluded, on: [2] },
      { key: "pool", label: usedJev(t) ? "Jev에 보낸 후보" : "순위 후보", n: t.pool.length, on: [3, 4] },
      { key: "result", label: "결과", n: run.response.items.length, on: [5] },
    ];
    const max = Math.log10(total + 1);
    els.funnel.hidden = false;
    els.funnel.innerHTML = cells.map((c) => `<div class="fcell${c.on.includes(run.step) ? " on" : ""}" data-key="${c.key}"`
      + ` style="flex:${(0.6 + Math.log10(c.n + 1) / max).toFixed(2)}"><b data-count="${c.n}">${shownCounts.get(c.key) ?? 0}</b><span>${esc(c.label)}</span></div>`).join('<i class="farrow">›</i>');
    for (const b of els.funnel.querySelectorAll("b[data-count]")) {
      const key = b.parentElement.dataset.key;
      const from = shownCounts.get(key) ?? 0;
      const to = Number(b.dataset.count);
      shownCounts.set(key, to);
      const t0 = performance.now();
      const tick = (now) => {
        const k = Math.min(1, (now - t0) / 900);
        b.textContent = Math.round(from + (to - from) * k).toLocaleString("ko-KR");
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  }

  // 3D 노드 클릭 → 패널에서 같은 레시피(재료) 행 강조. 재료 고르기 모드면 가진 재료에 더한다
  function onNodeSelect(n) {
    if (!n) return;
    if (els.pick.checked && n.kind === "ingredient" && !n.is_concept) { addPantry(n.id.slice(4)); return; }
    if (run) highlightRow(n.id);
  }

  function highlightRow(id) {
    for (const el of els.body.querySelectorAll(".hit")) el.classList.remove("hit");
    const row = els.body.querySelector(`[data-row="${CSS.escape(id)}"]`);
    if (row) { row.classList.add("hit"); row.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
  }

  // --- 공용 보기 조각 -------------------------------------------------------------------------------

  const L = () => run.t.labels || {};
  const chip = (id, cls = "") => `<span class="chip ${cls}" data-goto="${esc(id)}">${esc(name(id))}</span>`;

  function userView() {
    const t = run.t;
    const nodes = new Map();
    const links = new Map();
    const labels = [];
    for (const g of t.user.allergen_groups) {
      nodes.set(g, { color: REASON_COLOR.allergen, scale: 1.8 });
      labels.push({ id: g, text: `${name(g)} (알레르기)`, color: REASON_COLOR.allergen, px: 13 });
      for (const l of scene.incident.get(g) || []) {
        if (l.type !== "bundle_member" || l.s !== g) continue;
        links.set(l.id, { color: REASON_COLOR.allergen, alpha: 1 });
        nodes.set(l.t, { color: REASON_COLOR.allergen, scale: 1.4 });
        labels.push({ id: l.t, text: name(l.t), color: "#ffb4b8" });
      }
    }
    for (const i of t.user.hard_dislikes) {
      nodes.set(i, { color: COLOR.hardDislike, scale: 1.7 });
      labels.push({ id: i, text: `${name(i)} (절대 안 먹음)`, color: COLOR.hardDislike, px: 13 });
    }
    return { nodes, links, labels };
  }

  function exclusionText(e) {
    if (e.reason === "allergen") {
      const group = esc(name(e.source_group)) + (e.target_node !== e.source_group ? ` ⊂ ${esc(name(e.target_node))}` : "");
      return `${e.via.map((x) => esc(name(x))).join(" → ")} → <b>${group}</b>${e.certainty === "possible" ? ' <span class="possible-tag">포함 가능</span>' : ""}`;
    }
    if (e.reason === "hard_dislike_ingredient") return `${e.via.map((x) => esc(name(x))).join(" → ")} <span class="muted">(${esc(e.label)})</span>`;
    if (e.ingredient) return `${esc(name(e.ingredient))} <span class="muted">(${esc(e.label)})</span>`;
    return `${esc(e.label)}${e.detail ? ` <span class="muted">${esc(e.detail)}</span>` : ""}`;
  }

  function scoreCell(ans) {
    if (!ans) return '<td class="jv none" title="답 없음">-</td>';
    const lv = (L().levels_ko || [])[Math.round(ans.score * 4)] || "";
    const bg = `rgba(255,178,36,${(0.12 + 0.8 * ans.score).toFixed(2)})`;
    return `<td class="jv" style="background:${bg};opacity:${(0.35 + 0.65 * ans.confidence).toFixed(2)}" `
      + `title="${esc(lv)} · 점수 ${f2(ans.score)} · 확신도 ${f2(ans.confidence)}">${f2(ans.score)}</td>`;
  }

  // --- 단계 -----------------------------------------------------------------------------------------

  const STEPS = [
    // 1 못 먹는 것: 알레르기 그룹(묶음 구성원 포함)·절대 안 먹는 재료. Jev에는 보내지 않는다
    () => {
      const t = run.t;
      const view = userView();
      const notSent = (L().not_sent || []).map((x) => `<span class="chip">${esc(x)}</span>`).join("");
      const bits = [];
      if (t.user.allergen_groups.length) bits.push(`<div><b>알레르기</b> ${t.user.allergen_groups.map((g) => chip(g, "alert")).join("")}<span class="muted">들어 있을 수도 있는 재료까지 제외</span></div>`);
      if (t.user.hard_dislikes.length) bits.push(`<div><b>절대 안 먹음</b> ${t.user.hard_dislikes.map((i) => chip(i, "alert")).join("")}<span class="muted">확실히 들어간 것만 제외</span></div>`);
      if (t.user.spicy_max !== null) bits.push(`<div><b>매운맛 한도</b> ${t.user.spicy_max} <span class="muted">넘으면 제외</span></div>`);
      if (t.user.hard_cuisines.length) bits.push(`<div><b>절대 안 먹는 음식 종류</b> ${esc(t.user.hard_cuisines.join(", "))}</div>`);
      const html = `<p>${MODE_LABEL[run.mode]}${run.response.query ? ` "<b>${esc(run.response.query)}</b>"` : ""}. 추천은 언제나 <b>규칙으로 먼저 못 먹는 것을 뺀 뒤</b>에 순위를 정합니다.</p>`
        + `<div class="rows">${bits.join("") || '<div class="muted">제외 조건 없음</div>'}</div>`
        + `<p class="muted small-text">알레르기 판정은 컴파일된 지식 그래프(재료 → 포함 관계 → 알레르기 그룹)로만 합니다. 아래 정보는 Jev에 <b>보내지 않습니다</b>: ${notSent}</p>`;
      return { html, view };
    },
    // 2 요청 해석(규칙): 형태별로 후보를 어떻게 모으는지
    () => (run.mode === "dish" ? dishStep() : run.mode === "pantry" ? pantryStep() : randomStep()),
    // 3 제외(규칙): 확인한 레시피 중 빠진 것. 알레르기·절대 안 먹음은 경로를 따라 빛
    () => {
      const t = run.t;
      const filter = run.filter;
      const base = userView();
      const nodes = base.nodes;
      const links = base.links;
      const labels = filter ? [] : base.labels;
      const pulses = [];
      for (const c of t.checked) if (c.passed && !filter) nodes.set(c.recipe, { color: PLAY_COLOR.pass, scale: 1.05 });
      for (const [recipe, reason] of Object.entries(t.excluded)) {
        if (filter && recipe !== filter) continue;
        nodes.set(recipe, { color: REASON_COLOR[reason], scale: 1.35 });
        labels.push({ id: recipe, text: `${name(recipe)} · ${REASON_SHORT[reason]}`, color: REASON_COLOR[reason], priority: 50 });
        for (const e of run.byRecipe.get(recipe) || []) {
          for (const l of e.path_links) links.set(l, { color: REASON_COLOR[e.reason], alpha: 1 });
          if (e.reason === "allergen") {
            const chain = [e.target_node, ...(e.source_group !== e.target_node ? [e.source_group] : []), ...[...e.via].reverse(), recipe];
            for (const id of chain.slice(0, -1)) if (!nodes.has(id)) nodes.set(id, { scale: 1.2 });
            if (filter) {
              for (const id of e.via) labels.push({ id, text: name(id), color: "#ffb4b8" });
              labels.push({ id: e.source_group, text: `${name(e.source_group)} (알레르기 그룹)`, color: REASON_COLOR.allergen, px: 13 });
            }
            pulses.push({ nodes: chain, color: "#ff8a90" });
          } else if (e.reason === "hard_dislike_ingredient") {
            for (const id of e.via) if (!nodes.has(id)) nodes.set(id, { scale: 1.2 });
            pulses.push({ nodes: [...[...e.via].reverse(), recipe], color: "#ffb27a" });
          } else if (e.ingredient) nodes.set(e.ingredient, { scale: 1.2 });
        }
      }
      const counts = {};
      for (const reason of Object.values(t.excluded)) counts[reason] = (counts[reason] || 0) + 1;
      const rows = [...run.byRecipe].map(([recipe, rs]) => `<div class="excl${filter === recipe ? " on" : ""}" data-row="${esc(recipe)}" data-filter="${esc(recipe)}" title="클릭: 이 레시피 경로만 보기">`
        + `<b style="color:${REASON_COLOR[t.excluded[recipe]]}">${esc(name(recipe))}</b>`
        + rs.map((e) => `<div class="why">${exclusionText(e)}</div>`).join("") + "</div>");
      const checked = t.checked.length;
      const dishNote = (run.response.notes || []).find((n) => n.code === "dish_excluded");
      const html = `<p>확인한 레시피 <b>${checked}</b>개 중 <b>${Object.keys(t.excluded).length}</b>개 제외`
        + (Object.keys(counts).length ? ` (${Object.entries(counts).map(([k, v]) => `<span style="color:${REASON_COLOR[k]}">${REASON_SHORT[k]} ${v}</span>`).join(", ")})` : "")
        + `, 통과 ${checked - Object.keys(t.excluded).length}개. 빠진 레시피는 확인한 순서대로 땅으로 떨어지고, 행을 누르면 그 경로만 빛납니다.</p>`
        + (run.mode !== "pantry" ? '<p class="muted small-text">랜덤·요리 찾기는 필요한 후보 수가 모이면 확인을 멈추므로, 확인하지 않은 레시피는 판정하지 않았습니다.</p>' : "")
        + (dishNote ? `<p class="notice">${esc(dishNote.text)}</p>` : "")
        + (filter ? '<p class="muted">한 레시피만 보는 중 — 다시 누르면 전체</p>' : "")
        + (rows.length ? `<div class="excl-list">${rows.join("")}</div>` : '<p class="muted">제외된 레시피가 없습니다.</p>');
      return { html, view: { nodes, links, labels, pulses } };
    },
    // 4 Jev에 보낸 후보와 정보
    () => {
      const t = run.t;
      const nodes = new Map();
      const labels = [];
      for (const r of Object.keys(t.excluded)) nodes.set(r, { color: REASON_COLOR[t.excluded[r]], opacity: 0.3 });
      t.pool.forEach((r, i) => {
        const g = run.groupOf.get(r);
        const color = t.screened[r] !== undefined ? COLOR.screened : g ? COLOR[g] : PLAY_COLOR.candidate;
        nodes.set(r, { color, scale: 1.35 });
        if (i < LABELS) labels.push({ id: r, text: name(r), color, priority: i + 1 });
      });
      const jev = t.jev || t.failed_jev;
      let html = "";
      if (t.ranking === "jev" || t.jev_failed) {
        const sk = L().state_ko || {};
        const state = Object.entries(jev.state).map(([k, v]) => `<tr><th>${esc(sk[k] || k)}</th><td>${esc(Array.isArray(v) ? v.join(", ") : v)}</td></tr>`).join("");
        const ex = jev.candidates[0];
        html += `<p>규칙으로 고른 후보 <b>${t.pool.length}</b>개를 Jev에 보냅니다${Object.keys(t.screened).length ? ` (그중 <span style="color:${COLOR.screened}">${Object.keys(t.screened).length}개</span>는 관련 후보가 적어 Jev가 전체에서 걸러 보충)` : ""}.`
          + ` 레시피 id 대신 c0, c1… 같은 임시 key를 씁니다.</p>`
          + `<h4>Jev가 받은 사용자 정보</h4><table class="kv">${state || '<tr><td class="muted">없음</td></tr>'}</table>`
          + (ex ? `<h4>후보 요약 예 (${esc(ex.key)})</h4><pre class="json">${esc(JSON.stringify(ex.brief, null, 1))}</pre>` : "")
          + `<p class="muted small-text">보내지 않음: ${(L().not_sent || []).map(esc).join(", ")}</p>`;
        if (t.jev_failed) html += '<p class="notice">Jev가 응답하지 않아(또는 키 없음) 이 후보들은 규칙 점수로 순위를 정합니다.</p>';
      } else {
        html += `<p>규칙 점수로 순위를 정할 후보 <b>${t.pool.length}</b>개입니다(Jev를 쓰지 않음).</p>`;
      }
      html += `<h4>후보</h4><div class="rows">${t.pool.map((r) => `<div data-row="${esc(r)}">${chip(r)}`
        + (run.groupOf.get(r) ? `<span class="muted">${run.groupOf.get(r) === "ready" ? "지금 바로" : `${t.missing[r]}개 사면`}</span>` : "")
        + (t.screened[r] !== undefined ? `<span class="muted">걸러내기 ${f2(t.screened[r])}</span>` : "") + "</div>").join("")}</div>`;
      return { html: '<p class="muted small-text">후보가 수관 위 순위 무대 고리로 떠오릅니다(내 재료로는 지금 바로 = 안쪽 초록 고리).</p>' + html, view: { nodes, links: new Map(), labels } };
    },
    // 5 순위 판단: Jev 항목별 점수표(색 = 점수, 흐림 = 확신도) 또는 규칙 점수
    () => {
      const t = run.t;
      const nodes = new Map();
      const labels = [];
      for (const r of Object.keys(t.excluded)) nodes.set(r, { color: REASON_COLOR[t.excluded[r]], opacity: 0.25 });
      for (const r of t.ranked) {
        nodes.set(r.recipe, { color: r.shown ? PLAY_COLOR.rank : PLAY_COLOR.pass, scale: 1.1 + r.score * 0.6, opacity: r.shown ? 1 : 0.55 });
        if (r.rank <= LABELS) labels.push({ id: r.recipe, text: `${r.rank}위 ${name(r.recipe)} ${f2(r.score)}`, color: r.shown ? PLAY_COLOR.rank : "#cfc6b0", priority: r.rank });
      }
      let html;
      if (t.ranking === "jev") {
        const j = t.jev;
        const ak = L().aspect_ko || {};
        html = `<p>Jev는 후보마다 아래 질문에 5단계(${esc((L().levels_ko || []).join(" · "))})로 답하고 확신도를 붙입니다.`
          + ` 종합 J = 항목 점수의 가중 평균이고, 이 순서가 그대로 순위입니다. 무대 고리를 순위 순으로 돌며, 후보들 안에서 J가 높을수록 높이 섭니다(가장 낮은 후보 = 고리 높이).</p>`
          + `<ol class="questions">${j.aspects.map((a) => `<li><b>${esc(ak[a] || a)}</b> <span class="muted">× ${j.weights[a]}</span><div class="en">${esc(j.questions[a])}</div></li>`).join("")}</ol>`
          + '<p class="muted small-text">칸 색이 진할수록 점수가 높고, 흐릴수록 Jev 확신도가 낮습니다. Jev는 이유 문장을 주지 않으므로 점수와 확신도만 보입니다.</p>'
          + `<div class="table-wrap"><table class="scores jev"><thead><tr><th>순위</th><th>레시피</th>${j.aspects.map((a) => `<th title="${esc(ak[a] || a)}">${esc(a)}</th>`).join("")}<th>J</th><th title="가장 낮은 확신도">확신</th></tr></thead><tbody>`
          + t.ranked.map((r) => `<tr data-row="${esc(r.recipe)}" class="${r.shown ? "" : "muted"}"><td>${r.rank}</td><td>${chip(r.recipe)}</td>`
            + j.aspects.map((a) => scoreCell(j.answers[r.recipe]?.[a])).join("")
            + `<td><b>${f2(r.score)}</b></td><td>${f2(r.breakdown.J_conf)}</td></tr>`).join("")
          + "</tbody></table></div>";
      } else {
        const keys = Object.keys(t.ranked[0]?.breakdown || {});
        const w = (k) => (k === "S" ? `S × ${t.s_weight}` : t.rule_weights[k] !== undefined ? `× ${t.rule_weights[k]}` : "");
        const why = t.jev_failed ? "Jev가 응답하지 않아 규칙 점수로 대체했습니다. " : "";
        const randomNote = run.mode === "random" ? "랜덤(규칙)은 점수로 정렬하지 않고 섞은 순서 그대로 보여 줍니다. 점수는 참고용입니다. " : "";
        html = `<p>${why}${randomNote}규칙 점수 = 항목 값 × 가중치의 합${run.mode === "dish" ? `, 요리 찾기는 ${t.s_weight}·S + ${(1 - t.s_weight).toFixed(1)}·규칙 점수` : ""}. 무대에서는 후보들 안에서 점수가 높을수록 높이 섭니다.</p>`
          + `<p class="muted small-text">${keys.map((k) => `${esc(k)} ${esc(t.breakdown_labels[k] || "")} ${w(k)}`).join(" · ")}</p>`
          + `<div class="table-wrap"><table class="scores"><thead><tr><th>순위</th><th>레시피</th><th>점수</th>${keys.map((k) => `<th title="${esc(t.breakdown_labels[k] || k)}">${esc(k)}</th>`).join("")}</tr></thead><tbody>`
          + t.ranked.map((r) => `<tr data-row="${esc(r.recipe)}" class="${r.shown ? "" : "muted"}"><td>${r.rank}</td><td>${chip(r.recipe)}</td><td><b>${f2(r.score)}</b></td>`
            + keys.map((k) => `<td>${f2(r.breakdown[k])}</td>`).join("") + "</tr>").join("")
          + "</tbody></table></div>";
      }
      return { html: petalLegend() + html, view: { nodes, links: new Map(), labels } };
    },
    // 6 결과: 최종 레시피와 주재료 간선
    () => {
      const t = run.t;
      const nodes = new Map();
      const links = new Map();
      const labels = [];
      const owned = new Set(t.pantry.owned.map((o) => o.node));
      for (const r of t.ranked.filter((x) => x.shown)) {
        nodes.set(r.recipe, { color: PLAY_COLOR.rank, scale: 1.7 });
        labels.push({ id: r.recipe, text: `${r.rank}위 ${name(r.recipe)}`, color: PLAY_COLOR.rank, px: 13, priority: r.rank });
        for (const l of scene.incident.get(r.recipe) || []) {
          if (l.type !== "uses" || l.s !== r.recipe || !["main", "sub"].includes(l.role)) continue;
          links.set(l.id, { color: LINK_COLOR[l.role], alpha: 0.9 });
          if (!nodes.has(l.t)) nodes.set(l.t, run.mode === "pantry" && owned.has(l.t) ? { color: PLAY_COLOR.owned, scale: 1.3 } : { scale: 1.1 });
        }
      }
      const notes = petalLegend() + (run.response.notes || []).map((n) => `<p class="notice">${esc(n.text)}</p>`).join("");
      const html = `<p>추천 <b>${run.response.items.length}</b>개 · 제외 ${run.response.excluded_total}개 · 순위: ${t.ranking === "jev" ? `Jev(${esc(t.model)})` : "규칙 점수"}.`
        + " 레시피와 주재료·부재료 간선이 강조됩니다. 카드를 누르면 그 레시피로 이동합니다.</p>" + notes
        + (run.response.disclaimer ? `<p class="muted small-text">${esc(run.response.disclaimer)}</p>` : "");
      return { html, view: { nodes, links, labels } };
    },
  ];

  function randomStep() {
    const t = run.t;
    const nodes = new Map();
    const labels = [];
    t.checked.forEach((c, i) => {
      nodes.set(c.recipe, { color: PLAY_COLOR.candidate, scale: 1.25 });
      if (i < LABELS) labels.push({ id: c.recipe, text: `#${i + 1} ${name(c.recipe)}`, color: PLAY_COLOR.candidate, priority: i + 1 });
    });
    const need = t.ranking === "jev" || t.jev_failed ? `Jev에 보낼 ${t.pool.length}개` : `보여 줄 ${t.limit}개`;
    const html = `<p>seed <b>${t.seed}</b>로 레시피 전체를 섞고, 그 순서대로 하나씩 제외 조건을 확인해 ${need}가 모이면 멈춥니다.`
      + ` 이번에는 <b>${t.checked.length}</b>개를 확인했습니다(취향은 이 단계에서 보지 않음).</p>`
      + `<h4>섞은 순서(확인한 레시피)</h4><div class="rows">${t.checked.map((c, i) => `<div data-row="${esc(c.recipe)}"><span class="muted">#${i + 1}</span> ${chip(c.recipe)}</div>`).join("")}</div>`;
    return { html, view: { nodes, links: new Map(), labels } };
  }

  function pantryStep() {
    const t = run.t;
    const ok = L().owned_ko || {};
    const nodes = new Map();
    const links = new Map(t.pantry.owned_links.map((l) => [l, { color: PLAY_COLOR.ancestor, alpha: 0.95 }]));
    const labels = [];
    for (const o of t.pantry.owned) {
      if (o.because === "pantry") { nodes.set(o.node, { color: PLAY_COLOR.owned, scale: 1.8 }); labels.push({ id: o.node, text: name(o.node), color: PLAY_COLOR.owned, px: 13 }); }
      else if (o.because === "ancestor") { nodes.set(o.node, { color: PLAY_COLOR.ancestor, scale: 1.4 }); labels.push({ id: o.node, text: `${name(o.node)} (상위 분류)`, color: PLAY_COLOR.ancestor }); }
      else nodes.set(o.node, { color: PLAY_COLOR.staple, scale: 1, opacity: 0.6 });
    }
    const owned = new Set(t.pantry.owned.map((o) => o.node));
    for (const [g, ids] of Object.entries(t.groups)) {
      ids.forEach((r, i) => {
        nodes.set(r, { color: COLOR[g], scale: 1.3 });
        if (i < 8) labels.push({ id: r, text: `${name(r)}${g === "near" ? ` (+${t.missing[r]})` : ""}`, color: COLOR[g], priority: 20 + i });
        for (const l of scene.incident.get(r) || []) if (l.type === "uses" && l.s === r && owned.has(l.t)) links.set(l.id, { color: COLOR[g], alpha: 0.7 });
      });
    }
    const rowsOf = (g) => (t.groups[g] || []).map((r) => `<div data-row="${esc(r)}">${chip(r)}<span class="muted">가진 재료 ${t.uses_pantry[r]}줄${g === "near" ? ` · 부족 ${t.missing[r]}` : ""}</span></div>`);
    const html = `<p>가진 재료 ${t.pantry.input.map((i) => chip(i, "owned")).join("")}에 더해, 지식 그래프의 <b>is_a 상위 분류</b>와 기본 양념도 가진 것으로 봅니다.</p>`
      + `<div class="rows">${["ancestor", "staple"].map((k) => `<div><b>${esc(ok[k] || k)}</b> ${t.pantry.owned.filter((o) => o.because === k).slice(0, 30).map((o) => chip(o.node, k)).join("") || '<span class="muted">없음</span>'}</div>`).join("")}</div>`
      + `<p>그 재료를 쓰는 레시피를 후보로 잡고 제외 조건을 통과한 것을, 꼭 필요한 재료가 <span style="color:${COLOR.ready}">모두 있으면 "지금 바로"</span>, `
      + `<span style="color:${COLOR.near}">1~2개 부족하면 "조금만 사면"</span>으로 나눕니다(묶음은 규칙, 묶음 안 순서는 다음 단계). 확인 ${t.checked.length}개.</p>`
      + `<h4>지금 바로 ${t.groups.ready?.length || 0}</h4><div class="rows">${rowsOf("ready").join("")}</div>`
      + `<h4>조금만 사면 ${t.groups.near?.length || 0}</h4><div class="rows">${rowsOf("near").join("")}</div>`;
    return { html, view: { nodes, links, labels } };
  }

  function dishStep() {
    const t = run.t;
    const q = t.query;
    const sk = L().similarity_ko || {};
    const nodes = new Map();
    const labels = [];
    if (!q) return { html: '<p class="muted">질의 해석 결과가 없습니다.</p>', view: { nodes, links: new Map(), labels } };
    for (const i of q.ingredients) { nodes.set(i, { color: PLAY_COLOR.owned, scale: 1.8 }); labels.push({ id: i, text: `${name(i)} (문장 속 재료)`, color: PLAY_COLOR.owned, px: 13 }); }
    for (const a of q.anchors) labels.push({ id: a, text: `${name(a)} (같은 이름)`, color: "#fff", px: 13 });
    t.similarity.forEach((s, i) => {
      nodes.set(s.recipe, { color: s.passed === false ? REASON_COLOR.allergen : PLAY_COLOR.candidate, scale: 1 + s.S * 0.8, opacity: 0.4 + 0.6 * s.S });
      if (i < LABELS) labels.push({ id: s.recipe, text: `${name(s.recipe)} S ${f2(s.S)}`, color: PLAY_COLOR.candidate, priority: i + 1 });
    });
    const ruleText = (r) => {
      const conds = [];
      for (const [d, mm] of Object.entries(r.taste)) conds.push(`${d === "spicy" ? "매운맛" : d} ${mm.min != null ? `${mm.min} 이상` : ""}${mm.max != null ? `${mm.max} 이하` : ""}`);
      if (r.cuisine) conds.push(`음식 종류 = ${r.cuisine}`);
      if (r.title_any.length) conds.push(`제목에 ${r.title_any.join("·")} 중 하나`);
      return `<div><span class="chip word">${r.matched.map(esc).join(", ")}</span> → ${esc(conds.join(", "))}</div>`;
    };
    const parts = q.active;
    const html = `<p>문장 "<b>${esc(q.text)}</b>"를 <b>규칙</b>으로 해석합니다(Jev는 아직 쓰지 않음). 띄어쓰기를 지운 문장에서 키워드 표(config/v2.yaml)·재료 이름·같은 제목 레시피를 찾습니다.</p>`
      + `<h4>낱말</h4><div>${q.terms.map((w) => `<span class="chip word">${esc(w)}</span>`).join("") || '<span class="muted">없음</span>'}</div>`
      + `<h4>걸린 키워드 규칙</h4><div class="rows">${q.rules.map(ruleText).join("") || '<div class="muted">없음</div>'}</div>`
      + `<h4>문장 속 재료</h4><div>${q.ingredients.map((i) => chip(i, "owned")).join("") || '<span class="muted">없음</span>'}</div>`
      + `<h4>같은 이름 요리(앵커)</h4><div>${q.anchors.map((a) => chip(a)).join("") || '<span class="muted">없음</span>'}</div>`
      + `<p>유사도 S = 걸린 항목의 가중 평균: ${parts.map((k) => `${esc(sk[k] || k)} ×${q.weights[k]}`).join(" · ") || "없음"}. S가 높은 레시피부터 제외 조건을 확인해 후보를 모읍니다. 레시피가 제자리에서 S만큼 솟습니다.</p>`
      + `<div class="table-wrap"><table class="scores"><thead><tr><th>레시피</th><th>S</th>${parts.map((k) => `<th title="${esc(sk[k] || k)}">${esc(k)}</th>`).join("")}<th>확인</th></tr></thead><tbody>`
      + t.similarity.map((s) => `<tr data-row="${esc(s.recipe)}"><td>${chip(s.recipe)}</td><td><b>${f2(s.S)}</b></td>${parts.map((k) => `<td>${f2(s.parts[k])}</td>`).join("")}`
        + `<td>${s.passed === true ? "통과" : s.passed === false ? '<span style="color:#ff8a90">제외</span>' : '<span class="muted">-</span>'}</td></tr>`).join("")
      + "</tbody></table></div>";
    return { html, view: { nodes, links: new Map(), labels } };
  }

  // --- 결과 카드 ------------------------------------------------------------------------------------

  function cardsHtml() {
    const r = run.response;
    return r.items.map((it, i) => {
      const bars = it.breakdown.filter((b) => b.key !== "J_conf").map((b) => `<div class="bar"><span class="k" title="${esc(b.label)}">${esc(b.key)}</span>`
        + `<span class="track"><span style="width:${Math.round(b.value * 100)}%"></span></span><span class="v">${b.value.toFixed(2)}</span></div>`).join("");
      const lines = [];
      if (it.missing_text) lines.push(`<div class="miss">${esc(it.missing_text)}</div>`);
      for (const sub of it.substitutions || []) lines.push(`<div class="sub">${esc(sub.text)}</div>`);
      for (const n of [...(it.notes || []), ...(it.notices || [])]) lines.push(`<div class="note">${esc(n)}</div>`);
      if (it.label_check) lines.push(`<div class="note warn">${esc(it.label_check.text)}</div>`);
      return `<article class="rcard" data-goto="rcp:${esc(it.recipe_id)}">`
        + `<header><b>${i + 1}. ${esc(it.title)}</b><span class="score">${it.score.toFixed(2)}</span></header>`
        + `<div class="meta">${it.group_label ? `${esc(it.group_label)} · ` : ""}${esc(it.cuisine)} · 난이도 ${it.difficulty ?? "-"} · ${it.cook_time_min ?? "-"}분</div>`
        + `<div class="bars">${bars}</div>${lines.join("")}</article>`;
    }).join("") || '<p class="muted">추천할 레시피가 없습니다.</p>';
  }

  // --- hover 툴팁 -----------------------------------------------------------------------------------

  function tooltipExtra(n) {
    if (!run || n.kind !== "recipe") return "";
    const t = run.t;
    if (run.step >= 2 && t.excluded[n.id]) {
      return (run.byRecipe.get(n.id) || []).map((e) => `<div class="tip-ex">✕ ${esc(REASON_SHORT[e.reason])}: ${exclusionText(e)}</div>`).join("");
    }
    const r = run.rankOf.get(n.id);
    if (run.step >= 4 && r) {
      if (t.ranking === "jev") {
        const ans = t.jev.answers[n.id] || {};
        const ak = L().aspect_ko || {};
        return `<div>${r.rank}위 · Jev 종합 <b>${f2(r.score)}</b></div><table class="tip-table">`
          + t.jev.aspects.map((a) => `<tr><td>${esc(ak[a] || a)}</td><td>${f2(ans[a]?.score)}</td><td class="sub">확신 ${f2(ans[a]?.confidence)}</td></tr>`).join("") + "</table>";
      }
      return `<div>${r.rank}위 · 규칙 점수 <b>${f2(r.score)}</b></div><table class="tip-table">`
        + Object.entries(r.breakdown).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(t.breakdown_labels[k] || "")}</td><td>${f2(v)}</td></tr>`).join("") + "</table>";
    }
    if (run.step === 1 && run.mode === "dish") {
      const s = t.similarity.find((x) => x.recipe === n.id);
      if (s) return `<div>유사도 S <b>${f2(s.S)}</b></div>`;
    }
    if (run.step >= 3 && t.pool.includes(n.id)) return '<div class="sub">Jev(또는 규칙)에 보낸 후보</div>';
    return "";
  }

  load();
  return { tooltipExtra, stop, onNodeSelect, get active() { return run !== null; } };
}
