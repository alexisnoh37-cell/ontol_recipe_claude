// 분류 지도 배치(docs/plan.md 부록 H-10): 판정과 무관한 화면 좌표만 계산한다. 같은 데이터면 늘 같은 모양(결정적, force 없음).
//
// 위에서 내려다보는 납작한 원판이다. 높이(y)는 비워 두고 v2 재생이 판정 결과(가라앉음·탑)에만 쓴다.
//   안쪽 → 바깥 = 온톨로지 깊이: 가운데 알레르기 그룹 → 원천 재료·분류 고리 → 가공품 고리 → 레시피 띠
//   부채꼴 = 재료 분류(category). 가공품은 원천 재료 쪽 각도에, 레시피는 주재료가 있는 분류 부채꼴에 놓는다
//   그래서 간선 대부분이 짧고 바깥을 향한다. 고리 폭은 내용 수에 맞춰 늘어난다.

export const SECTOR = {
  coreR: 120, // 기본 알레르기 그룹 원
  bundleR: 200, // 묶음 그룹 원
  ringStart: 330, // 원천 재료 고리 시작 반지름
  gap: 70, // 고리 사이 간격
  ingStep: 40, // 재료 사이 간격(호·반지름 방향)
  recipeStep: 30, // 레시피 사이 간격
  labelPad: 110, // 레시피 띠 바깥 분류 이름까지
};

export const SECTOR_CAMERA = { pitchDeg: 58, distance: 4300, targetY: 0 };

const UNMAPPED = "(재료 미매칭)";
const wrap = (a) => ((a % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);

function anchorIngredient(recipe, incident) {
  // 레시피가 놓일 재료: 주재료 줄 중 번호가 가장 앞선 것, 없으면 매핑된 첫 줄(tree.js와 같은 규칙)
  const uses = (incident.get(recipe.id) || []).filter((l) => l.type === "uses" && l.s === recipe.id);
  const mains = uses.filter((l) => l.role === "main").sort((a, b) => a.line_no - b.line_no);
  const any = [...uses].sort((a, b) => a.line_no - b.line_no);
  return (mains[0] || any[0])?.t || null;
}

// 부채꼴 [a0, a0 + w] 안, 반지름 r0부터 바깥으로 items를 격자로 채운다(호 방향 칸 수는 반지름마다 다시 계산).
// order 순서대로 각도가 커지게 놓으므로, 정렬 키가 비슷한 것끼리 가까이 선다. 반환: 마지막 줄의 반지름
function fillWedge(items, a0, w, r0, step, pos) {
  let r = r0;
  let i = 0;
  const pad = Math.min(w * 0.08, step / Math.max(r0, 1));
  while (i < items.length) {
    const usable = Math.max(w - 2 * pad, 1e-6);
    const cols = Math.max(1, Math.floor((usable * r) / step));
    const row = items.slice(i, i + cols);
    row.forEach((n, j) => {
      const a = a0 + pad + (row.length === 1 ? usable / 2 : (usable * (j + 0.5)) / cols);
      pos.set(n.id, { x: r * Math.cos(a), y: 0, z: r * Math.sin(a) });
    });
    i += row.length;
    if (i < items.length) r += step;
  }
  return r;
}

/**
 * nodes: 장면 노드, incident: id → 간선 목록, byId: id → 노드.
 * 반환: { pos, labels: [{text, x, y, z, role}], rings: [반지름], dividers: [각도], bands: {raw, processed, recipe}, radius }
 */
export function sectorLayout(nodes, incident, byId) {
  const pos = new Map();
  const labels = [];
  const ings = nodes.filter((n) => n.kind === "ingredient");
  const recipes = nodes.filter((n) => n.kind === "recipe" && !n.adhoc);
  const catOf = (n) => n.category || "기타";

  // 레시피의 분류 = 주재료(없으면 첫 매핑 재료)의 분류
  const recipeCat = new Map();
  const anchor = new Map();
  for (const r of recipes) {
    const a = anchorIngredient(r, incident);
    anchor.set(r.id, a);
    recipeCat.set(r.id, a && byId.get(a) ? catOf(byId.get(a)) : UNMAPPED);
  }

  // 부채꼴 폭 = 재료 수 + 레시피 수 × 0.35 + 2(작은 분류도 이름이 들어갈 자리)
  const weight = new Map();
  for (const n of ings) weight.set(catOf(n), (weight.get(catOf(n)) || 0) + 1);
  for (const c of recipeCat.values()) weight.set(c, (weight.get(c) || 0) + 0.35);
  const cats = [...weight.keys()].sort((a, b) => (a === UNMAPPED) - (b === UNMAPPED) || a.localeCompare(b, "ko"));
  const total = cats.reduce((s, c) => s + weight.get(c) + 2, 0);
  const wedge = new Map();
  let at = -Math.PI / 2; // 첫 분류가 위(화면 안쪽)에서 시작
  for (const c of cats) {
    const w = ((weight.get(c) + 2) / total) * 2 * Math.PI;
    wedge.set(c, { a0: at, w });
    at += w;
  }

  // 가운데: 알레르기 그룹(기본 안쪽 원, 묶음 바깥 원)
  const groups = nodes.filter((n) => n.kind === "allergen_group").sort((a, b) => (a.category + a.id).localeCompare(b.category + b.id));
  const base = groups.filter((n) => n.group_kind !== "bundle");
  const bundles = groups.filter((n) => n.group_kind === "bundle");
  base.forEach((n, i) => {
    const a = (2 * Math.PI * i) / base.length;
    pos.set(n.id, { x: SECTOR.coreR * Math.cos(a), y: 0, z: SECTOR.coreR * Math.sin(a) });
  });
  bundles.forEach((n, i) => {
    const a = (2 * Math.PI * (i + 0.5)) / bundles.length;
    pos.set(n.id, { x: SECTOR.bundleR * Math.cos(a), y: 0, z: SECTOR.bundleR * Math.sin(a) });
  });

  // 원천 재료·분류 고리: 분류 부채꼴마다 이름순(분류 concept는 맨 앞)
  const byCat = (list) => {
    const m = new Map();
    for (const n of list) {
      if (!m.has(catOf(n))) m.set(catOf(n), []);
      m.get(catOf(n)).push(n);
    }
    return m;
  };
  let rawEnd = SECTOR.ringStart;
  for (const [c, list] of byCat(ings.filter((n) => n.layer === 2))) {
    list.sort((a, b) => (b.is_concept - a.is_concept) || a.name.localeCompare(b.name, "ko"));
    const { a0, w } = wedge.get(c);
    rawEnd = Math.max(rawEnd, fillWedge(list, a0, w, SECTOR.ringStart, SECTOR.ingStep, pos));
  }

  // 가공품 고리: 원천 재료(derived_from 대상) 쪽 각도 순으로 놓아 짧은 간선이 바깥을 향하게
  const procStart = rawEnd + SECTOR.gap;
  const sourceAngle = (n) => {
    for (const l of incident.get(n.id) || []) {
      if (l.type === "derived_from" && l.s === n.id && pos.has(l.t)) {
        const p = pos.get(l.t);
        return wrap(Math.atan2(p.z, p.x));
      }
    }
    return null;
  };
  let procEnd = procStart;
  for (const [c, list] of byCat(ings.filter((n) => n.layer === 3))) {
    const { a0, w } = wedge.get(c);
    const key = (n) => { const a = sourceAngle(n); return a === null ? 99 : wrap(a - a0); };
    list.sort((a, b) => key(a) - key(b) || a.name.localeCompare(b.name, "ko"));
    procEnd = Math.max(procEnd, fillWedge(list, a0, w, procStart, SECTOR.ingStep, pos));
  }

  // 레시피 띠: 분류 부채꼴 안에서 주재료 각도 순(같은 재료 레시피가 한데 모인다)
  const recStart = procEnd + SECTOR.gap + 40;
  let recEnd = recStart;
  const recByCat = new Map();
  for (const r of recipes) {
    const c = recipeCat.get(r.id);
    if (!recByCat.has(c)) recByCat.set(c, []);
    recByCat.get(c).push(r);
  }
  const counts = new Map();
  for (const [c, list] of recByCat) {
    const { a0, w } = wedge.get(c);
    const key = (r) => {
      const p = pos.get(anchor.get(r.id));
      return p ? wrap(Math.atan2(p.z, p.x) - a0) : 99;
    };
    list.sort((a, b) => key(a) - key(b) || (anchor.get(a.id) || "").localeCompare(anchor.get(b.id) || "") || a.id.localeCompare(b.id));
    recEnd = Math.max(recEnd, fillWedge(list, a0, w, recStart, SECTOR.recipeStep, pos));
    counts.set(c, list.length);
  }

  // 이름: 분류(바깥, 레시피 수), 고리 이름(빈 각도 쪽 한 줄)
  const labelR = recEnd + SECTOR.labelPad;
  let narrow = 0; // 좁은 부채꼴이 이어지면 이름 반지름을 엇갈려 겹치지 않게
  for (const c of cats) {
    const { a0, w } = wedge.get(c);
    const a = a0 + w / 2;
    const n = counts.get(c) || 0;
    const r = labelR + (w < 0.16 ? (narrow++ % 3) * 90 : 0);
    if (w >= 0.16) narrow = 0;
    labels.push({ text: n ? `${c} ${n}` : c, x: r * Math.cos(a), y: 0, z: r * Math.sin(a), role: "bunch", angle: a });
  }
  const ringLabelAngle = -Math.PI / 2 - 0.02; // 첫 분류 경계 바로 바깥(위쪽)
  const ringLabel = (text, r) => labels.push({ text, x: r * Math.cos(ringLabelAngle), y: 30, z: r * Math.sin(ringLabelAngle), role: "part" });
  ringLabel("알레르기 그룹", SECTOR.bundleR);
  ringLabel("원천 재료·분류", (SECTOR.ringStart + rawEnd) / 2);
  ringLabel("가공품", (procStart + procEnd) / 2);
  ringLabel("레시피", (recStart + recEnd) / 2);

  return {
    pos, labels,
    rings: [SECTOR.bundleR + 50, SECTOR.ringStart - 30, rawEnd + SECTOR.gap / 2, procEnd + (SECTOR.gap + 40) / 2, recEnd + 30],
    dividers: cats.map((c) => wedge.get(c).a0),
    bands: { raw: [SECTOR.ringStart, rawEnd], processed: [procStart, procEnd], recipe: [recStart, recEnd] },
    radius: recEnd + 30,
  };
}
