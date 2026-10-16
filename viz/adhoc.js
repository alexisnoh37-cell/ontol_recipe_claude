// 외부 레시피 분석 카드(docs/plan.md 부록 E). 화면은 판정하지 않는다: POST /analyze-recipe가 돌려준 매핑·알레르기 경로·
// 판정을 표로 보여 주고, 응답의 graph(임시 레시피 노드, 미매칭 줄 노드, 간선)를 기존 그래프 위에 겹쳐 그린다. 저장하지 않는다.

const EXAMPLE = {
  title: "AI 마파두부",
  text: "[양념장]\n두부 1모, 다진 돼지고기 100g\n두반장 1큰술, 굴소스 약간\n대파 1대, 다진 마늘 1큰술\n트러플 오일 1작은술\n물 200ml",
};

export function setupAdhoc({ scene, $, esc, select }) {
  const els = {
    title: $("#adhoc-title"), text: $("#adhoc-text"), subject: $("#adhoc-subject"), run: $("#adhoc-run"),
    clear: $("#adhoc-clear"), example: $("#adhoc-example"), status: $("#adhoc-status"), result: $("#adhoc-result"),
  };
  const name = (id) => esc(scene.byId.get(id)?.name ?? String(id).replace(/^[a-z]+:/, ""));
  const chip = (id, cls = "", text = null) => `<span class="chip ${cls}" data-goto="${esc(id)}">${text ?? name(id)}</span>`;

  // --- 판정 기준(구조만 / 페르소나 / 저장 프로필) ------------------------------------------------

  let personas = [];
  let profiles = [];
  function paintSubjects() {
    const keep = els.subject.value;
    const opt = (value, label) => `<option value="${esc(value)}">${esc(label)}</option>`;
    els.subject.innerHTML = opt("", "구조만 보기(판정 안 함)")
      + (personas.length ? `<optgroup label="골든셋 페르소나">${personas.map((p) => opt(`persona:${p.id}`, `${p.name} (${p.id})`)).join("")}</optgroup>` : "")
      + (profiles.length ? `<optgroup label="저장 프로필">${profiles.map((p) => opt(`profile:${p.id}`, `${p.display_name} (#${p.id})`)).join("")}</optgroup>` : "");
    if ([...els.subject.options].some((o) => o.value === keep)) els.subject.value = keep;
  }
  function loadSubjects() {
    // 따로 받아 그린다: 프로필 저장소(DB)가 늦거나 꺼져 있어도 페르소나는 바로 고를 수 있게
    const get = (url) => fetch(url).then((r) => (r.ok ? r.json() : [])).catch(() => []);
    get("/personas").then((xs) => { personas = xs; paintSubjects(); });
    get("/profiles").then((xs) => { profiles = xs; paintSubjects(); });
  }
  els.subject.addEventListener("focus", loadSubjects); // 재생 카드에서 만든 프로필도 보이게 다시 읽는다

  // --- 실행 ------------------------------------------------------------------------------------

  async function run() {
    const title = els.title.value.trim();
    const text = els.text.value;
    if (!title || !text.trim()) {
      els.status.textContent = "레시피 이름과 재료를 적어 주세요.";
      return;
    }
    const body = { title, text };
    const [kind, id] = els.subject.value.split(":");
    if (kind === "persona") body.persona_id = id;
    if (kind === "profile") body.profile_id = Number(id);
    els.run.disabled = true;
    els.status.textContent = "분석 중…";
    try {
      const res = await fetch("/analyze-recipe", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const json = await res.json();
      if (!res.ok) throw new Error(typeof json.detail === "string" ? json.detail : `요청 오류(${res.status})`);
      scene.setOverlay(json.graph);
      render(json);
      els.status.textContent = "";
      select(`rcp:${json.recipe_id}`);
    } catch (err) {
      els.status.textContent = err.message;
    } finally {
      els.run.disabled = false;
    }
  }

  function clear() {
    scene.setOverlay(null);
    scene.select(null);
    els.result.innerHTML = "";
    els.result.hidden = true;
    els.status.textContent = "";
  }

  // --- 결과 ------------------------------------------------------------------------------------

  function groupChip(a) {
    const strong = a.certainty === "definite";
    return chip(a.group, strong ? "alert" : "possible", `${esc(a.group_name)}${strong ? "" : " (포함 가능)"}`);
  }

  function lineCell(x, rid) {
    if (x.status === "mapped") {
      const isA = x.is_a.length ? `<div class="muted">is_a → ${x.is_a.map((a) => esc(a.name)).join(" → ")}</div>` : "";
      const src = x.derived_from.length
        ? `<div class="muted">원천 ← ${x.derived_from.map((s) => esc(s.name) + (s.certainty === "possible" ? "(가능)" : "")).join(", ")}</div>` : "";
      return chip(x.ingredient.node, "owned") + isA + src;
    }
    const raw = `raw:${rid}#${x.line_no}`;
    if (x.status === "concept") return `${chip(raw, "alert", "미매칭")} <span class="muted">분류 ${esc(x.concept.name)}에만 맞음</span>`;
    return `${chip(raw, "alert", "미매칭")} <span class="muted">온톨로지에 없음</span>`;
  }

  function allergenCell(x) {
    if (x.status !== "mapped") return '<span class="muted">판정 불가</span>';
    if (!x.allergens.length) return '<span class="muted">없음</span>';
    return x.allergens.map((a) => `<div>${groupChip(a)}${a.via.length > 1
      ? `<span class="muted">${a.via.map(name).join(" → ")}</span>` : ""}</div>`).join("");
  }

  function judgementBlock(j) {
    if (!j) return '<p class="muted">판정 기준을 고르면 그 사용자에게 제외되는지도 함께 봅니다.</p>';
    const who = j.allergen_groups.length ? j.allergen_groups.map((g) => chip(g.node, "alert", esc(g.name))).join("") : "알레르기 없음";
    const head = j.excluded
      ? '<p class="verdict bad">이 사용자에게는 <b>제외</b>됩니다.</p>'
      : '<p class="verdict ok">알레르기·미매칭·절대 불선호 기준을 <b>통과</b>했습니다.</p>';
    const rows = j.exclusions.map((e) => {
      const target = e.reason === "unmapped_ingredient" ? `${e.lines.join(", ")}번째 줄`
        : `${e.ingredient ? name(e.ingredient) : ""} → ${e.target_node ? name(e.target_node) : esc(e.target)}`
          + (e.source_group && e.source_group !== e.target_node ? ` (${name(e.source_group)})` : "");
      const tag = e.certainty === "possible" ? ' <span class="possible-tag">포함 가능</span>' : "";
      const goto = e.ingredient || (e.lines?.length ? e.path_links[0]?.replace(/^unm:/, "raw:") : null);
      return `<div class="excl"${goto ? ` data-goto="${esc(goto)}"` : ""}><b>${esc(e.label)}</b><span class="why">${target}${tag}</span></div>`;
    }).join("");
    return `${head}<p class="muted">기준 알레르기: ${who}</p>${rows ? `<div class="excl-list">${rows}</div>` : ""}`
      + `<p class="muted small">판정하지 않은 항목: ${j.not_checked.map(esc).join(", ")}(입력에 정보 없음)</p>`;
  }

  function render(r) {
    const c = r.counts;
    const missing = c.unmapped + c.concept;
    const summary = `<p>재료 ${c.lines}줄 중 <b>${c.mapped}줄</b> 매핑${missing ? `, <span class="warn">${missing}줄 미매칭</span>` : ""}</p>`;
    const groups = r.allergens.length ? r.allergens.map(groupChip).join("") : '<span class="muted">매핑된 재료 중에는 없음</span>';
    const table = `<table class="lines"><thead><tr><th>#</th><th>원문</th><th>재료</th><th>알레르기</th></tr></thead><tbody>${
      r.lines.map((x) => `<tr><td>${x.line_no}</td><td>${esc(x.raw_text)}</td><td>${lineCell(x, r.recipe_id)}</td><td>${allergenCell(x)}</td></tr>`).join("")
    }</tbody></table>`;
    const skipped = r.skipped.length ? `<p class="muted small">재료가 아니라서 뺀 항목: ${r.skipped.map(esc).join(", ")}</p>` : "";
    els.result.innerHTML = `${summary}<h4>걸리는 알레르기(레시피 전체)</h4><div>${groups}</div>`
      + `<h4>판정</h4>${judgementBlock(r.judgement)}<h4>재료 줄</h4>${table}${skipped}`
      + r.notice.map((t) => `<p class="note small">${esc(t)}</p>`).join("");
    els.result.hidden = false;
    for (const el of els.result.querySelectorAll("[data-goto]")) {
      el.style.cursor = "pointer";
      el.addEventListener("click", () => select(el.dataset.goto));
    }
  }

  els.run.addEventListener("click", run);
  els.clear.addEventListener("click", clear);
  els.example.addEventListener("click", () => { els.title.value = EXAMPLE.title; els.text.value = EXAMPLE.text; });
  loadSubjects();
}
