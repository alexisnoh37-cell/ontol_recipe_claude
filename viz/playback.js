// 추천 과정 6단계 재생(docs/plan.md 부록 D-5). 화면은 판정하지 않는다: POST /recommend(trace: true)가 돌려준 값만
// 색·높이·라벨로 바꾼다. 보유 재료를 편집하면 기존 API의 pantry(보유 재료 덮어쓰기)로 보낸다.

import { LINK_COLOR, PLAY_COLOR, REASON_COLOR, REASON_SHORT } from "./palette.js";

const STEP_TITLES = ["보유 재료(상속 포함)", "후보 레시피", "제외", "점수", "순위(다양성 보정)", "추천 카드"];
const AUTO_MS = 4000;
const SINK = -80; // 제외 레시피가 가라앉는 높이
const RISE = 150; // 통과 레시피가 점수 1.0일 때 올라가는 높이
const RANK_LABELS = 20;

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export function setupPlayback({ scene, $, attachSearch, ingredientIndex }) {
  const name = (id) => scene.byId.get(id)?.name ?? String(id).replace(/^[a-z]+:/, "");
  const els = {
    subject: $("#subject"), info: $("#subject-info"), pantry: $("#pantry-chips"), add: $("#pantry-add"),
    addList: $("#pantry-results"), reset: $("#pantry-reset"), run: $("#run"), status: $("#run-status"),
    player: $("#player"), dots: $("#step-dots"), prev: $("#prev"), next: $("#next"), auto: $("#auto"), stop: $("#stop"),
    title: $("#step-title"), body: $("#step-body"), cardsCard: $("#cards-card"), cards: $("#cards"),
  };
  const subjects = new Map(); // value → { kind, id, label, data, pantry: [id] }
  let current = null; // 선택한 프로필
  let pantry = []; // 편집 중인 보유 재료(정규 재료 id, 접두어 없음)
  let run = null; // { response, trace, step, recipeFilter }
  let timer = null;

  // --- 프로필 ------------------------------------------------------------------------------------

  async function loadSubjects() {
    const [personas, profiles] = await Promise.all([
      fetch("/personas").then((r) => (r.ok ? r.json() : [])).catch(() => []),
      fetch("/profiles").then((r) => (r.ok ? r.json() : [])).catch(() => []),
    ]);
    const groups = [];
    if (personas.length) {
      groups.push(`<optgroup label="골든셋 페르소나">${personas.map((p) => {
        subjects.set(`persona:${p.id}`, { kind: "persona", id: p.id, label: p.name, data: p, pantry: p.pantry.map((x) => x.id) });
        return `<option value="persona:${esc(p.id)}">${esc(p.name)} (${esc(p.id)})</option>`;
      }).join("")}</optgroup>`);
    }
    if (profiles.length) {
      groups.push(`<optgroup label="저장 프로필">${profiles.map((p) => {
        subjects.set(`profile:${p.id}`, { kind: "profile", id: p.id, label: p.display_name, data: p, pantry: p.pantry.map((x) => x.id) });
        return `<option value="profile:${p.id}">${esc(p.display_name)} (#${p.id})</option>`;
      }).join("")}</optgroup>`);
    }
    els.subject.innerHTML = groups.join("") || '<option value="">프로필 없음</option>';
    const want = new URLSearchParams(location.search).get("persona");
    if (want && subjects.has(`persona:${want}`)) els.subject.value = `persona:${want}`;
    chooseSubject(els.subject.value);
  }

  function chooseSubject(value) {
    stop();
    current = subjects.get(value) || null;
    pantry = current ? [...current.pantry] : [];
    renderSubject();
  }

  function renderSubject() {
    if (!current) {
      els.info.innerHTML = '<p class="muted">프로필이 없습니다.</p>';
      els.pantry.innerHTML = "";
      els.run.disabled = true;
      return;
    }
    const d = current.data;
    const allergies = d.allergen_groups.length
      ? d.allergen_groups.map((g) => `<span class="chip alert" data-goto="ag:${esc(g.id)}">${esc(g.name)}</span>`).join("")
      : '<span class="muted">없음</span>';
    const rows = [];
    if (d.description) rows.push(`<p class="desc">${esc(d.description)}</p>`);
    rows.push(`<dl><dt>요리 실력</dt><dd>${d.skill_level}</dd><dt>알레르기</dt><dd>${allergies}</dd>`
      + `<dt>조리기구</dt><dd>${esc((d.equipment || []).join(", ") || "없음")}</dd>`
      + (current.kind === "persona" ? `<dt>희망 시간</dt><dd>${d.max_time_min ? `${d.max_time_min}분` : "없음"}</dd>` : "")
      + "</dl>");
    els.info.innerHTML = rows.join("");
    const edited = !sameSet(pantry, current.pantry);
    els.pantry.innerHTML = pantry.map((id) => `<span class="chip removable" data-goto="ing:${esc(id)}">${esc(name(`ing:${id}`))}`
      + `<button type="button" data-remove="${esc(id)}" aria-label="${esc(name(`ing:${id}`))} 빼기">×</button></span>`).join("")
      || '<span class="muted">보유 재료 없음</span>';
    els.reset.hidden = !edited;
    els.run.disabled = false;
    bindGoto(els.info);
    bindGoto(els.pantry);
    for (const b of els.pantry.querySelectorAll("[data-remove]")) {
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        pantry = pantry.filter((x) => x !== b.dataset.remove);
        stop();
        renderSubject();
      });
    }
  }

  function bindGoto(root) {
    for (const el of root.querySelectorAll("[data-goto]")) {
      el.addEventListener("click", () => {
        if (!scene.byId.has(el.dataset.goto)) return;
        scene.select(el.dataset.goto);
        scene.flyTo(el.dataset.goto);
      });
    }
  }

  const sameSet = (a, b) => a.length === b.length && a.every((x) => b.includes(x));

  attachSearch(els.add, els.addList, ingredientIndex, (r) => {
    const id = r.id.slice(4);
    if (!pantry.includes(id)) pantry = [...pantry, id].sort();
    els.add.value = "";
    stop();
    renderSubject();
  });
  els.reset.addEventListener("click", () => { pantry = [...current.pantry]; stop(); renderSubject(); });
  els.subject.addEventListener("change", () => chooseSubject(els.subject.value));

  // --- 실행 ------------------------------------------------------------------------------------

  async function start() {
    if (!current) return;
    els.run.disabled = true;
    els.status.textContent = "추천 계산 중…";
    const body = { trace: true, limit: 10 };
    body[current.kind === "persona" ? "persona_id" : "profile_id"] = current.id;
    if (!sameSet(pantry, current.pantry)) body.pantry = pantry;
    try {
      const res = await fetch("/recommend", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const json = await res.json();
      if (!res.ok) throw new Error(typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail));
      run = { response: json, trace: json.trace, step: 0, recipeFilter: null, ...index(json.trace) };
      els.status.textContent = "";
      els.player.hidden = false;
      scene.select(null);
      show(0);
    } catch (err) {
      els.status.textContent = `실패: ${err.message}`;
    } finally {
      els.run.disabled = false;
    }
  }

  function index(t) {
    const byRecipe = new Map(); // 레시피 → 제외 행들
    for (const e of t.exclusions) {
      if (!byRecipe.has(e.recipe)) byRecipe.set(e.recipe, []);
      byRecipe.get(e.recipe).push(e);
    }
    const scored = new Map(t.scored.map((s) => [s.recipe, s]));
    const candidates = new Set(t.candidates.map((c) => c.recipe));
    return { byRecipe, scored, candidates };
  }

  function stop() {
    pause();
    if (!run) return;
    run = null;
    els.player.hidden = true;
    els.cardsCard.hidden = true;
    scene.setView(null);
    scene.setOffsets(new Map());
  }

  function pause() {
    if (timer) clearInterval(timer);
    timer = null;
    els.auto.textContent = "▶ 자동재생";
  }

  function show(step, { filter = null } = {}) {
    if (!run) return;
    run.step = Math.max(0, Math.min(5, step));
    run.recipeFilter = filter;
    const built = STEPS[run.step]();
    els.dots.innerHTML = STEP_TITLES.map((t, i) => `<button type="button" data-step="${i}" class="${i === run.step ? "on" : ""}" title="${esc(t)}">${i + 1}</button>`).join("");
    for (const b of els.dots.querySelectorAll("[data-step]")) b.addEventListener("click", () => { pause(); show(Number(b.dataset.step)); });
    els.title.textContent = `${run.step + 1}/6 ${STEP_TITLES[run.step]}`;
    els.body.innerHTML = built.html;
    bindGoto(els.body);
    for (const el of els.body.querySelectorAll("[data-filter]")) {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        pause();
        show(run.step, { filter: run.recipeFilter === el.dataset.filter ? null : el.dataset.filter });
      });
    }
    els.prev.disabled = run.step === 0;
    els.next.disabled = run.step === 5;
    els.cardsCard.hidden = run.step !== 5;
    if (run.step === 5) renderCards();
    scene.setView(built.view);
    scene.setOffsets(offsetsFor(run.step));
  }

  els.run.addEventListener("click", start);
  els.prev.addEventListener("click", () => { pause(); show(run.step - 1); });
  els.next.addEventListener("click", () => { pause(); show(run.step + 1); });
  els.stop.addEventListener("click", stop);
  els.auto.addEventListener("click", () => {
    if (timer) { pause(); return; }
    if (run.step === 5) show(0);
    els.auto.textContent = "❚❚ 멈춤";
    timer = setInterval(() => {
      if (!run || run.step >= 5) { pause(); return; }
      show(run.step + 1);
    }, AUTO_MS);
  });

  // --- 단계별 보기 ------------------------------------------------------------------------------

  function offsetsFor(step) {
    const off = new Map();
    if (step < 2) return off;
    for (const r of Object.keys(run.trace.excluded)) off.set(r, SINK);
    if (step >= 3) for (const s of run.trace.scored) off.set(s.recipe, s.score * RISE);
    return off;
  }

  function ownedStyles(strong) {
    const nodes = new Map();
    for (const o of run.trace.pantry.owned) {
      if (o.because === "pantry") nodes.set(o.node, { color: PLAY_COLOR.owned, scale: strong ? 1.7 : 1.2 });
      else if (o.because === "ancestor") nodes.set(o.node, { color: PLAY_COLOR.ancestor, scale: strong ? 1.4 : 1 });
      else nodes.set(o.node, { color: PLAY_COLOR.staple, scale: 1, opacity: strong ? 1 : 0.6 });
    }
    return nodes;
  }

  const STEPS = [
    // 1 보유 재료: 입력 재료, 기본 양념, is_a 상속으로 보유 간주된 상위 재료
    () => {
      const t = run.trace;
      const nodes = ownedStyles(true);
      const links = new Map(t.pantry.owned_links.map((l) => [l, { color: PLAY_COLOR.ancestor, alpha: 0.95 }]));
      const ancestors = t.pantry.owned.filter((o) => o.because === "ancestor");
      const labels = [
        ...t.pantry.input.map((id) => ({ id, text: name(id), color: PLAY_COLOR.owned, px: 13 })),
        ...ancestors.map((o) => ({ id: o.node, text: `${name(o.node)} (상속)`, color: PLAY_COLOR.ancestor })),
        ...t.pantry.staples.map((id) => ({ id, text: name(id), color: "#9aa1ad", px: 11 })),
      ];
      const html = `<p>입력한 보유 재료 <b>${t.pantry.input.length}</b>개, 기본 양념 <b>${t.pantry.staples.length}</b>개(보유로 간주),`
        + ` is_a 상위 재료 <b>${ancestors.length}</b>개를 보유로 간주합니다.</p>`
        + section("보유 재료", t.pantry.input.map((id) => chip(id, "owned")))
        + section("is_a 상속", ancestors.map((o) => `${chip(o.node, "ancestor")}<span class="muted">← ${o.from.map(name).map(esc).join(", ")}</span>`), "list")
        + section("기본 양념", t.pantry.staples.map((id) => chip(id, "staple")));
      return { html, view: { nodes, links, labels } };
    },
    // 2 후보: main·sub 재료 중 하나라도 보유(또는 대체)한 레시피와 그 근거 줄
    () => {
      const t = run.trace;
      const nodes = ownedStyles(false);
      const links = new Map();
      const rows = [];
      for (const c of t.candidates) {
        nodes.set(c.recipe, { color: PLAY_COLOR.candidate, scale: 1.3 });
        const basis = c.lines.filter((l) => l.basis);
        for (const l of basis) {
          if (l.link) links.set(l.link, { color: LINK_COLOR[l.role], alpha: 0.95 });
          if (l.node) nodes.set(l.node, { ...(nodes.get(l.node) || {}), color: PLAY_COLOR.owned, scale: 1.4 });
          if (l.use) nodes.set(l.use, { color: PLAY_COLOR.owned, scale: 1.4 });
        }
        rows.push(`${chip(c.recipe)}<span class="muted">${basis.map((l) => esc(name(l.node)) + (l.use ? `(대체: ${esc(name(l.use))})` : "")).join(", ")}</span>`);
      }
      const total = [...scene.byId.values()].filter((n) => n.kind === "recipe").length;
      const labels = t.candidates.map((c) => ({ id: c.recipe, text: name(c.recipe), color: PLAY_COLOR.candidate }));
      const html = `<p>레시피 ${total}개 중 주재료·부재료를 하나라도 보유(또는 대체)한 <b>${t.candidates.length}</b>개가 후보입니다.`
        + ' 나머지는 후보가 아니어서 이후 단계에 나오지 않습니다.</p>' + section("후보와 근거 재료", rows, "list");
      return { html, view: { nodes, links, labels } };
    },
    // 3 제외: 알레르기는 그룹 → via 경로 → 레시피로 빛이 올라가고 빨갛게 가라앉음, 절대 불선호 주황, 나머지 회색
    () => {
      const t = run.trace;
      const filter = run.recipeFilter;
      const nodes = new Map();
      const links = new Map();
      const labels = [];
      const pulses = [];
      for (const r of run.candidates) if (!t.excluded[r] && !filter) nodes.set(r, { color: PLAY_COLOR.pass, scale: 1.1 });
      for (const g of t.user.allergen_groups) {
        nodes.set(g, { scale: 1.3 });
        labels.push({ id: g, text: name(g), color: REASON_COLOR.allergen, px: 13 });
      }
      for (const [recipe, reason] of Object.entries(t.excluded)) {
        if (filter && recipe !== filter) continue;
        nodes.set(recipe, { color: REASON_COLOR[reason], scale: 1.35 });
        labels.push({ id: recipe, text: `${name(recipe)} · ${REASON_SHORT[reason]}`, color: REASON_COLOR[reason] });
        for (const e of run.byRecipe.get(recipe) || []) {
          const color = REASON_COLOR[e.reason];
          for (const l of e.path_links) links.set(l, { color, alpha: 1 });
          if (e.reason === "allergen") {
            const chain = [e.target_node, ...(e.source_group !== e.target_node ? [e.source_group] : []), ...[...e.via].reverse(), recipe];
            for (const id of chain.slice(0, -1)) if (!nodes.has(id)) nodes.set(id, { scale: 1.2 });
            for (const id of e.via) labels.push({ id, text: name(id), color: "#ffb4b8" });
            if (e.source_group !== e.target_node) labels.push({ id: e.source_group, text: name(e.source_group), color: REASON_COLOR.allergen });
            pulses.push({ nodes: chain, color: "#ff8a90" });
          } else if (e.reason === "hard_dislike_ingredient") {
            const chain = [...[...e.via].reverse(), recipe];
            for (const id of e.via) { if (!nodes.has(id)) nodes.set(id, { scale: 1.2 }); labels.push({ id, text: name(id), color: "#ffc59e" }); }
            pulses.push({ nodes: chain, color: "#ffb27a" });
          } else if (e.ingredient) {
            nodes.set(e.ingredient, { scale: 1.2 });
          }
        }
      }
      const counts = {};
      for (const reason of Object.values(t.excluded)) counts[reason] = (counts[reason] || 0) + 1;
      const rows = [];
      for (const [recipe, rs] of run.byRecipe) {
        const on = filter === recipe ? " on" : "";
        rows.push(`<div class="excl${on}" data-filter="${esc(recipe)}" title="클릭: 이 레시피 경로만 보기">`
          + `<b style="color:${REASON_COLOR[t.excluded[recipe]]}">${esc(name(recipe))}</b>`
          + rs.map((e) => `<div class="why">${exclusionText(e)}</div>`).join("") + "</div>");
      }
      const userBits = [];
      if (t.user.allergen_groups.length) userBits.push(`알레르기 ${t.user.allergen_groups.map((g) => esc(name(g))).join(", ")}`);
      if (t.user.hard_dislikes.length) userBits.push(`절대 불선호 ${t.user.hard_dislikes.map((g) => esc(name(g))).join(", ")}`);
      if (t.user.spicy_max !== null) userBits.push(`매운맛 한도 ${t.user.spicy_max}`);
      if (t.user.max_time_min !== null) userBits.push(`조리시간 ${t.user.max_time_min}분 이내(절대)`);
      const html = `<p>필터: ${userBits.join(" · ") || "없음"}</p>`
        + `<p>후보 ${run.candidates.size}개 중 <b>${Object.keys(t.excluded).length}</b>개 제외`
        + (Object.keys(counts).length ? ` (${Object.entries(counts).map(([k, v]) => `<span style="color:${REASON_COLOR[k]}">${REASON_SHORT[k]} ${v}</span>`).join(", ")})` : "")
        + `. 남은 ${run.candidates.size - Object.keys(t.excluded).length}개가 점수 단계로 갑니다.</p>`
        + (filter ? '<p class="muted">한 레시피만 보는 중 — 다시 클릭하면 전체</p>' : "")
        + (rows.length ? `<div class="excl-list">${rows.join("")}</div>` : '<p class="muted">제외된 후보가 없습니다.</p>');
      return { html, view: { nodes, links, labels, pulses } };
    },
    // 4 점수: 통과 레시피가 점수만큼 올라감(hover: I·K·T·P·D·M)
    () => {
      const t = run.trace;
      const nodes = new Map();
      for (const r of Object.keys(t.excluded)) nodes.set(r, { color: REASON_COLOR[t.excluded[r]], opacity: 0.35 });
      const byScore = [...t.scored].sort((a, b) => a.score_rank - b.score_rank);
      for (const s of byScore) nodes.set(s.recipe, { color: PLAY_COLOR.pass, scale: 1.2 + s.score * 0.4 });
      // 겹치면 점수 순위가 높은 라벨만 보이고 나머지는 마우스를 올리면 보인다(scene.js 겹침 정리)
      const labels = byScore.slice(0, RANK_LABELS).map((s) => ({ id: s.recipe, text: `${name(s.recipe)} ${s.score.toFixed(3)}`, priority: s.score_rank }));
      const keys = Object.keys(t.breakdown_labels);
      const html = `<p>필터를 통과한 <b>${t.scored.length}</b>개가 점수만큼 위로 올라갑니다. 레시피에 마우스를 올리면 항목별 점수가 보입니다.</p>`
        + `<p class="muted">가중치: ${keys.map((k) => `${k} ${t.weights[k]}`).join(" · ")}</p>`
        + `<table class="scores"><thead><tr><th>점수순</th><th>레시피</th><th>점수</th>${keys.map((k) => `<th title="${esc(t.breakdown_labels[k])}">${k}</th>`).join("")}</tr></thead><tbody>`
        + byScore.map((s) => `<tr><td>${s.score_rank}</td><td>${chip(s.recipe)}</td><td>${s.score.toFixed(3)}</td>`
          + keys.map((k) => `<td>${s.breakdown[k].toFixed(2)}</td>`).join("") + "</tr>").join("")
        + "</tbody></table>";
      return { html, view: { nodes, links: new Map(), labels } };
    },
    // 5 순위: 다양성 보정으로 자리가 바뀐 레시피 표시
    () => {
      const t = run.trace;
      const nodes = new Map();
      for (const r of Object.keys(t.excluded)) nodes.set(r, { color: REASON_COLOR[t.excluded[r]], opacity: 0.25 });
      const labels = [];
      for (const s of t.scored) {
        if (!s.shown) { nodes.set(s.recipe, { color: PLAY_COLOR.pass, opacity: 0.4 }); continue; }
        const color = s.moved_by_diversity ? PLAY_COLOR.moved : PLAY_COLOR.rank;
        nodes.set(s.recipe, { color, scale: 1.5 });
        labels.push({ id: s.recipe, color, px: 13, priority: s.final_rank,
          text: `${s.final_rank}위 ${name(s.recipe)}${s.moved_by_diversity ? ` (점수 ${s.score_rank}위)` : ""}` });
      }
      const moved = t.scored.filter((s) => s.moved_by_diversity).length;
      const html = `<p>상위 ${t.limit}개를 보여 줍니다. 다양성 보정(같은 음식 종류·주재료 한도)으로 자리가 바뀐 레시피 <b>${moved}</b>개는 주황색입니다.</p>`
        + `<ol class="ranks">${t.scored.map((s) => `<li class="${s.shown ? "" : "muted"}">${chip(s.recipe)} ${s.score.toFixed(3)}`
          + (s.moved_by_diversity ? ` <span class="moved">점수 ${s.score_rank}위 → ${s.final_rank}위</span>` : "")
          + (s.shown ? "" : " <span class=\"muted\">(표시 범위 밖)</span>") + "</li>").join("")}</ol>`;
      return { html, view: { nodes, links: new Map(), labels } };
    },
    // 6 추천 카드: 최종 추천 레시피와 주재료 간선
    () => {
      const t = run.trace;
      const nodes = new Map();
      const links = new Map();
      const labels = [];
      for (const s of t.scored.filter((x) => x.shown)) {
        nodes.set(s.recipe, { color: PLAY_COLOR.rank, scale: 1.6 });
        labels.push({ id: s.recipe, text: `${s.final_rank}위 ${name(s.recipe)}`, color: PLAY_COLOR.rank, px: 13 });
        for (const l of scene.incident.get(s.recipe) || []) {
          if (l.type !== "uses" || l.s !== s.recipe || l.role !== "main") continue;
          links.set(l.id, { color: LINK_COLOR.main, alpha: 0.9 });
          if (!nodes.has(l.t)) nodes.set(l.t, { scale: 1.1 });
        }
      }
      const html = `<p>추천 ${run.response.items.length}개. 아래 "추천 카드"에 항목별 점수, 부족 재료, 대체 안내가 있습니다.`
        + ` 제외된 레시피는 ${run.response.excluded_total}개입니다.</p>`
        + (run.response.disclaimer ? `<p class="muted">${esc(run.response.disclaimer)}</p>` : "");
      return { html, view: { nodes, links, labels } };
    },
  ];

  function exclusionText(e) {
    const label = esc(e.label);
    if (e.reason === "allergen") {
      const path = e.via.map((x) => esc(name(x))).join(" → ");
      const group = esc(name(e.source_group)) + (e.target_node !== e.source_group ? ` ⊂ ${esc(name(e.target_node))}` : "");
      return `${path} → <b>${group}</b>${e.certainty === "possible" ? ' <span class="possible-tag">포함 가능</span>' : ""}`
        + (e.detail?.includes("선택 재료") ? ' <span class="muted">(선택 재료)</span>' : "");
    }
    if (e.reason === "hard_dislike_ingredient") return `${e.via.map((x) => esc(name(x))).join(" → ")} <span class="muted">(${label})</span>`;
    if (e.ingredient) return `${esc(name(e.ingredient))} <span class="muted">(${label})</span>`;
    return `${label}${e.detail ? ` <span class="muted">${esc(e.detail)}</span>` : ""}`;
  }

  function chip(id, cls = "") {
    return `<span class="chip ${cls}" data-goto="${esc(id)}">${esc(name(id))}</span>`;
  }

  function section(title, items, kind = "chips") {
    if (!items.length) return "";
    return `<h4>${esc(title)}</h4>` + (kind === "list" ? `<div class="rows">${items.map((x) => `<div>${x}</div>`).join("")}</div>` : `<div>${items.join("")}</div>`);
  }

  // --- 추천 카드 --------------------------------------------------------------------------------

  function renderCards() {
    const r = run.response;
    els.cards.innerHTML = r.items.map((it, i) => {
      const s = run.scored.get(`rcp:${it.recipe_id}`);
      const bars = it.breakdown.map((b) => `<div class="bar"><span class="k" title="${esc(b.label)}">${esc(b.key)}</span>`
        + `<span class="track"><span style="width:${Math.round(b.value * 100)}%"></span></span><span class="v">${b.value.toFixed(2)}</span></div>`).join("");
      const lines = [];
      if (it.missing_text) lines.push(`<div class="miss">${esc(it.missing_text)}</div>`);
      if (it.nice_to_have_text) lines.push(`<div class="muted">${esc(it.nice_to_have_text)}</div>`);
      for (const sub of it.substitutions) lines.push(`<div class="sub">${esc(sub.text)}</div>`);
      for (const n of [...it.notes, ...it.notices]) lines.push(`<div class="note">${esc(n)}</div>`);
      if (it.label_check) lines.push(`<div class="note warn">${esc(it.label_check.text)}</div>`);
      return `<article class="rcard" data-goto="rcp:${esc(it.recipe_id)}">`
        + `<header><b>${i + 1}. ${esc(it.title)}</b><span class="score">${it.score.toFixed(3)}</span></header>`
        + `<div class="meta">${esc(it.cuisine)} · 난이도 ${it.difficulty} · ${it.cook_time_min}분`
        + (s?.moved_by_diversity ? ` · <span class="moved">다양성 보정(점수 ${s.score_rank}위)</span>` : "") + "</div>"
        + `<div class="bars">${bars}</div>${lines.join("")}</article>`;
    }).join("") || '<p class="muted">추천할 레시피가 없습니다.</p>';
    bindGoto(els.cards);
  }

  // --- hover 툴팁에 붙일 재생 정보 ---------------------------------------------------------------

  function tooltipExtra(n) {
    if (!run || n.kind !== "recipe") return "";
    const t = run.trace;
    if (run.step >= 2 && t.excluded[n.id]) {
      return (run.byRecipe.get(n.id) || []).map((e) => `<div class="tip-ex">✕ ${esc(REASON_SHORT[e.reason])}: ${exclusionText(e)}</div>`).join("");
    }
    const s = run.scored.get(n.id);
    if (run.step >= 3 && s) {
      const rows = Object.keys(t.breakdown_labels).map((k) => `<tr><td>${k}</td><td>${esc(t.breakdown_labels[k])}</td>`
        + `<td>${s.breakdown[k].toFixed(2)}</td><td class="sub">× ${t.weights[k]} = ${s.weighted[k].toFixed(3)}</td></tr>`).join("");
      return `<div>점수 <b>${s.score.toFixed(3)}</b> · 점수 ${s.score_rank}위 → 최종 ${s.final_rank}위</div><table class="tip-table">${rows}</table>`;
    }
    if (run.step >= 1 && run.candidates.has(n.id)) return '<div class="sub">후보</div>';
    if (run.step >= 1) return '<div class="sub">후보 아님(보유한 주재료·부재료 없음)</div>';
    return "";
  }

  loadSubjects();
  return { tooltipExtra, stop, get active() { return run !== null; } };
}
