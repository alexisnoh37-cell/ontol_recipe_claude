// 나무 배치(docs/plan.md 부록 D-9): 판정과 무관한 화면 좌표만 계산한다. 같은 데이터면 늘 같은 모양(결정적, force 없음).
//
//   뿌리  1층 알레르기 그룹: 줄기 밑에서 아래·바깥으로 퍼진다(묶음 그룹은 더 깊고 넓게)
//   줄기  2층 원천 재료·분류: 좁은 기둥. 분류(category)마다 같은 방향, 기둥 높이를 따라 쌓인다
//   가지  3층 가공품: 줄기 꼭대기에서 분류 방향으로 위·바깥으로 뻗는다(줄기와 같은 분류 각도)
//   잎    4층 레시피: 반구(돔) 표면에 고르게 흩뿌린 점(해바라기 배치)에 방향 순서대로 배정
//         - 주재료(ingredient): 레시피가 쓰는 주재료 노드의 방향 → 같은 재료 레시피가 한 부채꼴에 모인다
//         - 음식 종류(cuisine): 음식 종류별 부채꼴(레시피 수에 비례한 폭)

export const TREE = {
  rootTop: -600, // 뿌리가 시작하는 높이(줄기 밑)
  trunkBottom: -540,
  trunkTop: -60,
  trunkR: 70,
  branchY: -40, // 가지가 시작하는 높이
  branchFrom: 90,
  branchLen: 440,
  branchRise: 0.72, // 가지가 바깥으로 1 갈 때 올라가는 비율
  domeY: 120, // 반구 중심 높이
  domeR: 720,
  thetaMax: 1.35, // 반구 꼭대기에서 잎이 내려오는 최대 각도(rad, 약 77도)
};

export const TREE_CAMERA = { pitchDeg: 12, distance: 2700, targetY: 80 };

const GOLDEN = Math.PI * (3 - Math.sqrt(5));

function categoryAngles(nodes) {
  // 줄기(2층)와 가지(3층)가 같은 분류 각도를 쓰도록 분류 전체를 한 번에 나눈다
  const keys = [...new Set(nodes.filter((n) => n.kind === "ingredient").map((n) => n.category || "기타"))].sort();
  const width = (2 * Math.PI) / Math.max(keys.length, 1);
  return { angle: new Map(keys.map((k, i) => [k, i * width])), width };
}

function byCategory(list) {
  const out = new Map();
  for (const n of [...list].sort((a, b) => a.id.localeCompare(b.id))) {
    const k = n.category || "기타";
    if (!out.has(k)) out.set(k, []);
    out.get(k).push(n);
  }
  return out;
}

// 반구 표면의 고른 점 N개(면적이 같은 띠, 해바라기 각도). 방위각 순으로 정렬해 돌려준다.
function domePoints(count) {
  const pts = [];
  const cosMax = Math.cos(TREE.thetaMax);
  for (let i = 0; i < count; i++) {
    const u = (i + 0.5) / count;
    const theta = Math.acos(1 - u * (1 - cosMax));
    const phi = (i * GOLDEN) % (2 * Math.PI);
    pts.push({ theta, phi });
  }
  return pts.sort((a, b) => a.phi - b.phi || a.theta - b.theta);
}

function domeXYZ(theta, phi) {
  const r = TREE.domeR * Math.sin(theta);
  return { x: r * Math.cos(phi), y: TREE.domeY + TREE.domeR * Math.cos(theta), z: r * Math.sin(phi) };
}

const wrap = (a) => ((a % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);

// 레시피가 매달릴 재료: 주재료 줄 중 번호가 가장 앞선 것, 없으면 매핑된 첫 줄(식품안전나라는 역할이 모두 sub)
function anchorIngredient(recipe, incident) {
  const uses = (incident.get(recipe.id) || []).filter((l) => l.type === "uses" && l.s === recipe.id);
  const mains = uses.filter((l) => l.role === "main").sort((a, b) => a.line_no - b.line_no);
  const any = [...uses].sort((a, b) => a.line_no - b.line_no);
  return (mains[0] || any[0])?.t || null;
}

/**
 * nodes: 장면 노드, incident: id → 간선 목록, kind: "ingredient" | "cuisine".
 * 반환: { pos: Map<id, {x,y,z}>, labels: [{text, x, y, z, px, role}] }
 */
export function treeLayout(nodes, incident, byId, kind) {
  const pos = new Map();
  const labels = [];
  const { angle: catAngle, width } = categoryAngles(nodes);

  // 뿌리: 기본 그룹은 줄기 밑 둘레, 묶음 그룹은 더 깊고 넓게
  const groups = nodes.filter((n) => n.kind === "allergen_group").sort((a, b) => (a.category + a.id).localeCompare(b.category + b.id));
  const base = groups.filter((n) => n.group_kind !== "bundle");
  const bundles = groups.filter((n) => n.group_kind === "bundle");
  base.forEach((n, i) => {
    const a = (2 * Math.PI * i) / base.length;
    const r = 120 + (i % 3) * 55;
    pos.set(n.id, { x: r * Math.cos(a), y: TREE.rootTop - r * 0.55, z: r * Math.sin(a) });
  });
  bundles.forEach((n, i) => {
    const a = (2 * Math.PI * (i + 0.5)) / bundles.length;
    pos.set(n.id, { x: 330 * Math.cos(a), y: TREE.rootTop - 260, z: 330 * Math.sin(a) });
  });

  // 줄기: 분류 방향마다 기둥 높이를 따라 쌓는다(분류 concept는 줄기 꼭대기 가운데 가까이)
  for (const [cat, list] of byCategory(nodes.filter((n) => n.kind === "ingredient" && n.layer === 2))) {
    const a0 = catAngle.get(cat);
    list.forEach((n, j) => {
      const t = list.length > 1 ? j / (list.length - 1) : 0.5;
      const a = a0 + ((j % 3) - 1) * width * 0.3;
      const r = n.is_concept ? TREE.trunkR * 0.25 : TREE.trunkR * (0.65 + 0.35 * ((j % 2) ? 1 : 0.5));
      const y = n.is_concept ? TREE.trunkTop + 20 : TREE.trunkBottom + (TREE.trunkTop - TREE.trunkBottom) * t;
      pos.set(n.id, { x: r * Math.cos(a), y, z: r * Math.sin(a) });
    });
  }

  // 가지: 줄기 꼭대기에서 분류 방향으로 뻗는다. 분류 안에서는 가지를 따라 줄지어 선다
  for (const [cat, list] of byCategory(nodes.filter((n) => n.kind === "ingredient" && n.layer === 3))) {
    const a0 = catAngle.get(cat);
    list.forEach((n, j) => {
      const d = TREE.branchFrom + (TREE.branchLen - TREE.branchFrom) * ((j + 1) / list.length);
      const a = a0 + ((j % 2) ? 1 : -1) * width * 0.18;
      pos.set(n.id, { x: d * Math.cos(a), y: TREE.branchY + d * TREE.branchRise + ((j % 2) ? 10 : -10), z: d * Math.sin(a) });
    });
  }

  // 잎: 레시피마다 방향(정렬 키)을 정하고, 반구의 고른 점을 방위각 순으로 배정
  const recipes = nodes.filter((n) => n.kind === "recipe" && !n.adhoc);
  const keyed = recipes.map((n) => {
    if (kind === "cuisine") return { n, group: n.cuisine || "기타" };
    const ing = anchorIngredient(n, incident);
    const p = ing ? pos.get(ing) : null;
    return { n, group: ing || "", phi: p ? wrap(Math.atan2(p.z, p.x)) : null };
  });
  let order;
  if (kind === "cuisine") {
    const cuisines = [...new Set(keyed.map((k) => k.group))].sort();
    keyed.forEach((k) => { k.rank = cuisines.indexOf(k.group); });
    order = keyed.sort((a, b) => a.rank - b.rank || a.n.id.localeCompare(b.n.id));
  } else {
    // 매달 재료가 없는 레시피(전부 미매칭)는 한쪽(방위각 맨 끝)에 모은다
    order = keyed.sort((a, b) => (a.phi ?? 99) - (b.phi ?? 99) || a.group.localeCompare(b.group) || a.n.id.localeCompare(b.n.id));
  }
  const pts = domePoints(order.length);
  // 정렬 키 순서와 방위각 순서를 맞추되, 주재료 모드에서는 시작 방위를 첫 재료 방향에 맞춰 돌린다
  const shift = kind === "ingredient" && order.length && order[0].phi !== null ? order[0].phi - pts[0].phi : 0;
  const bunches = new Map(); // 묶음(재료·음식 종류) → 점 목록(라벨 위치용)
  order.forEach((k, i) => {
    const p = pts[i];
    const xyz = domeXYZ(p.theta, p.phi + shift);
    pos.set(k.n.id, xyz);
    if (!bunches.has(k.group)) bunches.set(k.group, []);
    bunches.get(k.group).push({ ...p, phi: p.phi + shift });
  });

  // 라벨: 나무 부위 이름 + 큰 잎 무리 이름(음식 종류 전부, 주재료는 레시피가 많은 것만)
  labels.push({ text: "뿌리 · 알레르기 그룹", x: -430, y: TREE.rootTop - 200, z: 0, role: "part" });
  labels.push({ text: "줄기 · 원천 재료·분류", x: -150, y: (TREE.trunkBottom + TREE.trunkTop) / 2, z: 0, role: "part" });
  labels.push({ text: "가지 · 가공품", x: -TREE.branchLen - 60, y: TREE.branchY + TREE.branchLen * TREE.branchRise * 0.45, z: 0, role: "part" });
  labels.push({ text: "잎 · 레시피", x: -TREE.domeR * 0.75 - 80, y: TREE.domeY + TREE.domeR * 0.8, z: 0, role: "part" });
  const minBunch = kind === "cuisine" ? 1 : Math.max(8, Math.round(order.length / 60));
  const big = [...bunches.entries()].filter(([g, ps]) => g && ps.length >= minBunch)
    .sort((a, b) => b[1].length - a[1].length).slice(0, kind === "cuisine" ? 20 : 18);
  // 무리 이름: 가운데 방위각(원형 평균). 무리는 꼭대기~가장자리 부채꼴이라 평균 높이가 비슷해 겹치므로,
  // 방위각 순으로 이웃한 무리끼리 높이(극각)를 세 단계로 엇갈려 놓는다. 수관 표면보다 조금 바깥에 띄운다
  const centers = big.map(([g, ps]) => {
    const sx = ps.reduce((s, p) => s + Math.cos(p.phi), 0);
    const sz = ps.reduce((s, p) => s + Math.sin(p.phi), 0);
    return { g, n: ps.length, phi: wrap(Math.atan2(sz, sx)) };
  }).sort((a, b) => a.phi - b.phi);
  const tiers = [0.5, 0.85, 1.18];
  centers.forEach((c, i) => {
    const p = domeXYZ(tiers[i % tiers.length], c.phi);
    const k = 1.06;
    const name = kind === "cuisine" ? c.g : byId.get(c.g)?.name || c.g;
    labels.push({ text: `${name} ${c.n}`, x: p.x * k, y: TREE.domeY + (p.y - TREE.domeY) * k, z: p.z * k, role: "bunch" });
  });
  return { pos, labels };
}
