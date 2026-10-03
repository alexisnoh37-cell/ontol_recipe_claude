// 3D 장면: 층 배치, 노드·간선 표현, 강조(재질만 변경), 재생용 보기(view)·높이 이동·경로 빛. 판정하지 않는다(docs/plan.md 부록 D).
//
// 성능 규칙(부록 D-6, 목표 레시피 1천 개)
//   - y는 층으로 고정(fy), x·z만 warmup 동안 계산하고 cooldownTicks(0)으로 멈춘다.
//   - 레시피-재료 간선은 기본 숨김. 숨긴 간선은 three 객체를 만들지 않는다(3d-force-graph가 visible만 생성).
//   - 강조는 노드 메시의 재질만 바꾼다(graphData 재설정 금지). 재질은 (색, 투명도)별로 공유한다.
//   - 높이 이동은 node.y만 바꾸고 d3ReheatSimulation()으로 위치 동기화 한 번(cooldownTicks 0이라 force tick은 돌지 않음).
//   - 텍스트 스프라이트는 층·구역 이름, 선택·재생 단계가 고른 노드만. 화면에서 일정한 크기(sizeAttenuation 끔).

import ForceGraph3D from "https://cdn.jsdelivr.net/npm/3d-force-graph@1.80.1/+esm";
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.186.1/+esm";

import { BUNDLE_DY, LAYER_LABEL, LAYER_Y, NODE_COLOR, linkAlpha, linkBaseColor, linkRestAlpha, rgba } from "./palette.js";

const DIM = { select: 0.07, play: 0.025 }; // 강조 밖 노드 투명도(재생 중에는 더 흐리게)
const LINK_DIM = { select: 0.03, play: 0.01 };
const RADIUS = { group: 120, bundle: 190, ingredient: 270, processed: 290, recipe: 250 };
const CAMERA = { pitchDeg: 35, distance: 2100, targetY: -20 }; // 위에서 35도 내려다봄
const LABEL_PX = { layer: 20, sector: 15, selected: 16, node: 12 };
const MAX_NEIGHBOR_LABELS = 60;
const FAINT_LINK = 0.28; // 선택 강조 안의 흐린 경로(포함 가능·선택 재료)
const FAINT_NODE = 0.55;

export function nodeStyle(n) {
  if (n.kind === "allergen_group") {
    return { color: NODE_COLOR[n.category], shape: n.group_kind === "bundle" ? "octa" : "box", hollow: n.category === "custom" };
  }
  if (n.kind === "recipe") return { color: NODE_COLOR.recipe, shape: "cylinder" };
  if (n.is_concept) return { color: NODE_COLOR.concept, shape: "sphere", wire: true };
  if (n.layer === 3) return { color: NODE_COLOR.processed, shape: "icosa" };
  return { color: NODE_COLOR.raw, shape: "sphere" };
}

// --- 배치 -----------------------------------------------------------------------------------------

function sectorLayout(items, keyOf, radius, y) {
  // 같은 key(category·cuisine)끼리 같은 각도 구역에 모은다. 구역 중심 각도도 돌려준다(구역 이름 표시용).
  const keys = [...new Set(items.map(keyOf))].sort();
  const width = (2 * Math.PI) / Math.max(keys.length, 1);
  const sectors = [];
  keys.forEach((key, k) => {
    const members = items.filter((n) => keyOf(n) === key);
    const center = k * width;
    sectors.push({ key, angle: center, y, radius });
    members.forEach((n, j) => {
      const t = members.length > 1 ? j / (members.length - 1) - 0.5 : 0;
      const angle = center + t * width * 0.8;
      const r = radius + ((j % 4) - 1.5) * 28;
      n.ax = r * Math.cos(angle);
      n.az = r * Math.sin(angle);
      n.x = n.ax;
      n.z = n.az;
    });
  });
  return sectors;
}

function initialLayout(nodes) {
  for (const n of nodes) {
    n.fy = LAYER_Y[n.layer] + (n.group_kind === "bundle" ? BUNDLE_DY : 0);
    n.y = n.fy;
    n.baseY = n.fy;
  }
  const groups = nodes.filter((n) => n.kind === "allergen_group");
  for (const [list, r] of [[groups.filter((n) => n.group_kind !== "bundle"), RADIUS.group],
                           [groups.filter((n) => n.group_kind === "bundle"), RADIUS.bundle]]) {
    list.sort((a, b) => (a.category + a.id).localeCompare(b.category + b.id));
    list.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / list.length;
      n.fx = n.x = r * Math.cos(angle);
      n.fz = n.z = r * Math.sin(angle);
    });
  }
  const ing2 = nodes.filter((n) => n.kind === "ingredient" && n.layer === 2);
  const ing3 = nodes.filter((n) => n.kind === "ingredient" && n.layer === 3);
  const recipes = nodes.filter((n) => n.kind === "recipe");
  return [
    ...sectorLayout(ing2, (n) => n.category || "기타", RADIUS.ingredient, LAYER_Y[2]),
    ...sectorLayout(ing3, (n) => n.category || "기타", RADIUS.processed, LAYER_Y[3]),
    ...sectorLayout(recipes, (n) => n.cuisine || "기타", RADIUS.recipe, LAYER_Y[4]),
  ];
}

function anchorForce() {
  // 각자 구역 중심 쪽으로 당긴다(x·z만). 3층 가공품은 구역 배치를 우선(원천 재료 쪽 인력보다 세게),
  // 레시피는 주재료 간선이 더 세게 당기도록 약하게.
  let nodes = [];
  const force = (alpha) => {
    for (const n of nodes) {
      if (n.ax === undefined || n.fx !== undefined) continue;
      const k = (n.kind === "recipe" ? 0.04 : n.layer === 3 ? 0.3 : 0.09) * alpha;
      n.vx += (n.ax - n.x) * k;
      n.vz += (n.az - n.z) * k;
    }
  };
  force.initialize = (ns) => { nodes = ns; };
  return force;
}

function linkStrength(l, byId) {
  if (l.type === "uses") return l.role === "main" ? 0.12 : 0.02;
  const crossesProcessed = byId.get(l.s).layer === 3 || byId.get(l.t).layer === 3;
  if (l.type === "derived_from") return 0.015; // 가공품 → 원천: 약하게(3층이 가운데로 뭉치지 않게)
  if (l.type === "is_a") return crossesProcessed ? 0.08 : 0.3;
  if (l.type === "allergen") return 0.02;
  return 0;
}

// --- 그리기 도구 ---------------------------------------------------------------------------------

const GEOMETRY = {
  sphere: new THREE.SphereGeometry(4, 8, 6),
  icosa: new THREE.IcosahedronGeometry(4.6, 0),
  box: new THREE.BoxGeometry(9, 9, 9),
  octa: new THREE.OctahedronGeometry(11, 0),
  cylinder: new THREE.CylinderGeometry(9, 9, 5, 14),
};
const EDGES = { box: new THREE.EdgesGeometry(GEOMETRY.box), octa: new THREE.EdgesGeometry(GEOMETRY.octa) };
const RING = new THREE.TorusGeometry(7, 0.5, 4, 16);
const PULSE = new THREE.SphereGeometry(3.2, 10, 8);

const materials = new Map();
function material(kind, color, opacity) {
  const key = `${kind}|${color}|${opacity.toFixed(3)}`;
  let m = materials.get(key);
  if (!m) {
    const opts = { color, transparent: opacity < 1, opacity, depthWrite: opacity >= 1 };
    m = kind === "line" ? new THREE.LineBasicMaterial(opts)
      : kind === "wire" ? new THREE.MeshBasicMaterial({ ...opts, wireframe: true })
      : kind === "glow" ? new THREE.MeshBasicMaterial(opts)
      : new THREE.MeshLambertMaterial(opts);
    materials.set(key, m);
  }
  return m;
}

// 화면에서 일정한 크기의 글자(px = 글자 높이 픽셀). 위치는 노드 위쪽(center.y < 0).
function textSprite(text, { px = 12, color = "#e6e8ec", background = "rgba(14,15,18,0.72)", above = true } = {}) {
  const scale = 3; // 선명도
  const size = 16 * scale;
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const font = `600 ${size}px "Malgun Gothic", "Apple SD Gothic Neo", sans-serif`;
  ctx.font = font;
  const pad = 5 * scale;
  canvas.width = Math.ceil(ctx.measureText(text).width) + pad * 2;
  canvas.height = size + pad * 2;
  ctx.font = font;
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = color;
  ctx.textBaseline = "middle";
  ctx.fillText(text, pad, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: texture, depthWrite: false, depthTest: false, transparent: true, sizeAttenuation: false,
  }));
  sprite.userData.px = px * (canvas.height / size); // 배경 여백 포함 높이
  sprite.userData.aspect = canvas.width / canvas.height;
  if (above) sprite.center.set(0.5, -0.35);
  sprite.renderOrder = 20;
  return sprite;
}

function disposeSprite(sprite) {
  sprite.material.map.dispose();
  sprite.material.dispose();
}

// --- 장면 ----------------------------------------------------------------------------------------

export function createScene(el, data, { tooltip, onSelect } = {}) {
  const nodes = data.nodes.map((n) => ({ ...n }));
  const links = data.links.map((l) => ({ ...l, s: l.source, t: l.target })); // s·t: 원래 id(라이브러리가 source를 객체로 바꿈)
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const linkById = new Map(links.map((l) => [l.id, l]));
  const incident = new Map(nodes.map((n) => [n.id, []]));
  for (const l of links) {
    incident.get(l.s)?.push(l);
    incident.get(l.t)?.push(l);
  }
  const sectors = initialLayout(nodes);

  const state = {
    layers: { 1: true, 2: true, 3: true, 4: true },
    linkTypes: { is_a: true, derived_from: true, allergen: true, bundle_member: true, uses: false },
    selection: null, // 클릭한 노드의 강조 { mode, nodes: Map<id, style>, links: Map<link, style>, labels }
    view: null, // 재생 단계가 정한 강조(같은 모양). 선택이 있으면 선택이 우선
    selected: null,
  };
  const focus = () => state.selection || state.view;
  const objects = new Map(); // node id → THREE.Mesh

  function nodeVisible(n) {
    return state.layers[n.layer];
  }
  function linkVisible(l) {
    const a = byId.get(l.s);
    const b = byId.get(l.t);
    if (!nodeVisible(a) || !nodeVisible(b)) return false;
    const f = focus();
    return state.linkTypes[l.type] || (f !== null && f.links.has(l));
  }
  function linkColor(l) {
    const f = focus();
    if (!f) return rgba(linkBaseColor(l), linkRestAlpha(l));
    const st = f.links.get(l);
    if (!st) return rgba(linkBaseColor(l), LINK_DIM[f.mode]);
    return rgba(st.color || linkBaseColor(l), st.alpha ?? linkAlpha(l));
  }

  function buildNode(n) {
    const st = nodeStyle(n);
    const mesh = new THREE.Mesh(GEOMETRY[st.shape]);
    mesh.userData.style = st;
    if (st.hollow) {
      mesh.add(new THREE.LineSegments(EDGES[st.shape]));
    }
    if (n.confidence === "low") {
      const ring = new THREE.Mesh(RING);
      ring.rotation.x = Math.PI / 2;
      ring.userData.ring = true;
      mesh.add(ring);
    }
    objects.set(n.id, mesh);
    paintNode(n);
    return mesh;
  }

  function paintNode(n) {
    const mesh = objects.get(n.id);
    if (!mesh) return;
    const st = mesh.userData.style;
    const f = focus();
    const over = f ? f.nodes.get(n.id) : null;
    const opacity = !f ? 1 : over ? (over.opacity ?? 1) : DIM[f.mode];
    const color = over?.color || st.color;
    mesh.material = st.hollow && !over?.color ? material("solid", color, opacity * 0.18)
      : material(st.wire && !over?.color ? "wire" : "solid", color, opacity);
    for (const child of mesh.children) {
      child.material = child.userData.ring ? material("solid", NODE_COLOR.lowConfidence, opacity * 0.8)
        : material("line", color, opacity);
    }
    const s = (state.selected === n.id ? 1.6 : 1) * (over?.scale ?? 1);
    mesh.scale.set(s, s, s);
  }

  const graph = new ForceGraph3D(el, { controlType: "orbit" })
    .backgroundColor("#0e0f12")
    .showNavInfo(false)
    .nodeId("id")
    .nodeThreeObject(buildNode)
    .nodeVisibility(nodeVisible)
    .nodeLabel((n) => (tooltip ? tooltip(n) : n.name))
    .linkVisibility(linkVisible)
    .linkColor(linkColor)
    .linkOpacity(1)
    .linkWidth(0)
    .enableNodeDrag(false)
    .warmupTicks(nodes.length > 600 ? 120 : 160)
    .cooldownTicks(0)
    .d3VelocityDecay(0.35)
    .onNodeClick((n) => select(n.id))
    .onBackgroundClick(() => select(null));

  graph.d3Force("center", null);
  graph.d3Force("anchor", anchorForce());
  graph.d3Force("charge").strength(-18).distanceMax(160);
  graph.d3Force("link")
    .distance((l) => {
      const dy = Math.abs(LAYER_Y[byId.get(l.s).layer] - LAYER_Y[byId.get(l.t).layer]);
      return Math.hypot(dy, 18);
    })
    .strength((l) => linkStrength(l, byId));

  const tData = performance.now();
  graph.graphData({ nodes, links });
  const tLayout = performance.now();
  const fixedLabels = decorate(graph.scene(), sectors);
  const timings = { graphData: tLayout - tData, decorate: performance.now() - tLayout };

  function resetCamera(ms = 0) {
    const pitch = (CAMERA.pitchDeg * Math.PI) / 180;
    graph.cameraPosition(
      { x: 0, y: CAMERA.targetY + CAMERA.distance * Math.sin(pitch), z: CAMERA.distance * Math.cos(pitch) },
      { x: 0, y: CAMERA.targetY, z: 0 }, ms);
  }
  resetCamera();

  function refreshLinks() {
    graph.linkVisibility((l) => linkVisible(l)).linkColor((l) => linkColor(l));
  }

  // --- 라벨(화면 일정 크기) -------------------------------------------------------------------

  const labelCache = new Map(); // `${text}|${color}|${px}` → sprite
  let shownLabels = []; // [{ sprite, id }]

  function pxToScale(px) {
    const cam = graph.camera();
    const h = el.clientHeight || 1;
    return (px * 2 * Math.tan((cam.fov * Math.PI) / 360)) / h;
  }
  function rescale(sprite) {
    const s = pxToScale(sprite.userData.px);
    sprite.scale.set(s * sprite.userData.aspect, s, 1);
  }
  function placeLabel(entry) {
    const n = byId.get(entry.id);
    entry.sprite.position.set(n.x, n.y + 6, n.z);
  }
  function applyLabels() {
    const want = focus()?.labels || [];
    for (const { sprite } of shownLabels) graph.scene().remove(sprite);
    shownLabels = [];
    for (const lb of want) {
      const n = byId.get(lb.id);
      if (!n || !nodeVisible(n)) continue;
      const key = `${lb.text}|${lb.color || ""}|${lb.px || LABEL_PX.node}`;
      let sprite = labelCache.get(key);
      if (!sprite) {
        sprite = textSprite(lb.text, { px: lb.px || LABEL_PX.node, color: lb.color || "#e6e8ec" });
        labelCache.set(key, sprite);
      }
      rescale(sprite);
      const entry = { sprite, id: lb.id };
      placeLabel(entry);
      graph.scene().add(sprite);
      shownLabels.push(entry);
    }
    if (labelCache.size > 600) { // 오래 쓰면 캐시를 비움(보이는 것은 다음 applyLabels에서 다시 만든다)
      const used = new Set(shownLabels.map((e) => e.sprite));
      for (const [k, sp] of labelCache) if (!used.has(sp)) { disposeSprite(sp); labelCache.delete(k); }
    }
  }

  // --- 강조 ------------------------------------------------------------------------------------

  function repaint() {
    const sectorOpacity = focus() ? 0.3 : 1; // 강조 중에는 구역 이름을 흐리게(노드 라벨이 읽히도록)
    for (const sp of fixedLabels) if (sp.userData.sector) sp.material.opacity = sectorOpacity;
    for (const n of nodes) paintNode(n);
    refreshLinks();
    applyLabels();
    syncPulses();
  }

  function selectionFocus(id) {
    const n = byId.get(id);
    const ls = new Map();
    const ns = new Map([[id, {}]]);
    const neighbors = [];
    for (const l of incident.get(id)) {
      ls.set(l, {});
      const other = l.s === id ? l.t : l.s;
      if (!ns.has(other)) { ns.set(other, {}); neighbors.push(other); }
    }
    // 알레르기 경로 전체(closure via → 기본 그룹 → 그 그룹을 포함한 묶음).
    // 재료는 자기 경로, 레시피는 재료 줄마다의 경로. 포함 가능(possible)·선택 재료 경로는 흐린 선(FAINT).
    // 같은 간선·노드가 진한 경로와 흐린 경로에 함께 있으면 진한 쪽을 따른다.
    const pathNodes = [];
    const groups = new Map(); // 그려진 기본 그룹 → 진한 경로가 있는지(점검·디버깅용)
    const mark = (x, faint) => {
      const cur = ns.get(x);
      if (!cur) { ns.set(x, faint ? { opacity: FAINT_NODE } : {}); pathNodes.push(x); }
      else if (!faint && cur.opacity !== undefined) ns.set(x, {});
    };
    const markLink = (l, faint) => {
      const cur = ls.get(l);
      if (!cur) ls.set(l, faint ? { alpha: FAINT_LINK } : {});
      else if (!faint && cur.alpha !== undefined) ls.set(l, {});
    };
    const addPaths = (ingId, optional) => {
      for (const a of byId.get(ingId)?.allergens || []) {
        const faint = optional || a.certainty === "possible";
        groups.set(a.group, (groups.get(a.group) || false) || !faint);
        for (const lid of a.path_links) {
          const l = linkById.get(lid);
          if (!l) continue;
          markLink(l, faint);
          mark(l.s, faint);
          mark(l.t, faint);
        }
        for (const l of incident.get(a.group)) {
          if (l.type !== "bundle_member" || l.t !== a.group) continue;
          markLink(l, faint);
          mark(l.s, faint);
        }
      }
    };
    if (n.kind === "ingredient") addPaths(id, false);
    if (n.kind === "recipe") {
      for (const l of incident.get(id)) if (l.type === "uses" && l.s === id) addPaths(l.t, l.optional);
    }
    const order = (x) => (byId.get(x).kind === "recipe" ? 1 : 0); // 재료·그룹 라벨을 먼저
    const labeled = [...pathNodes, ...neighbors.sort((a, b) => order(a) - order(b))].slice(0, MAX_NEIGHBOR_LABELS);
    const labels = [{ id, text: n.name, px: LABEL_PX.selected, color: "#ffffff" },
      ...labeled.map((x) => ({ id: x, text: byId.get(x).name, color: "#c8cdd6" }))];
    return { mode: "select", nodes: ns, links: ls, labels, groups };
  }

  function select(id) {
    state.selected = id;
    state.selection = id === null ? null : selectionFocus(id);
    repaint();
    onSelect?.(id === null ? null : byId.get(id));
  }

  // 재생 단계 보기: { nodes: Map<id, {color, scale, opacity}>, links: Map<linkId, {color, alpha}>, labels, pulses }
  function setView(view) {
    if (view === null) {
      state.view = null;
    } else {
      const ls = new Map();
      for (const [lid, st] of view.links || []) {
        const l = linkById.get(lid);
        if (l) ls.set(l, st);
      }
      state.view = { mode: "play", nodes: view.nodes || new Map(), links: ls, labels: view.labels || [], pulses: view.pulses || [] };
    }
    repaint();
  }

  // --- 높이 이동(재생 3~6단계: 제외 레시피는 가라앉고 통과 레시피는 점수만큼 올라감) ---------

  let moveAnim = null;
  function setOffsets(offsets, ms = 700) {
    // offsets: Map<id, dy>. 없는 노드는 원래 높이로.
    const moving = [];
    for (const n of nodes) {
      const to = n.baseY + (offsets.get(n.id) || 0);
      if (Math.abs(to - n.y) > 0.01) moving.push({ n, from: n.y, to });
    }
    if (moveAnim) cancelAnimationFrame(moveAnim);
    if (!moving.length) return;
    const t0 = performance.now();
    const step = (now) => {
      const k = ms <= 0 ? 1 : Math.min(1, (now - t0) / ms);
      const e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      for (const m of moving) m.n.y = m.n.fy = m.from + (m.to - m.from) * e;
      graph.d3ReheatSimulation(); // cooldownTicks 0: force tick 없이 위치만 한 번 동기화
      for (const entry of shownLabels) placeLabel(entry);
      moveAnim = k < 1 ? requestAnimationFrame(step) : null;
    };
    moveAnim = requestAnimationFrame(step);
  }

  // --- 경로 빛(알레르기·절대 불선호 경로를 따라 그룹 → 레시피 쪽으로 이동) -------------------

  let pulses = [];
  let pulseAnim = null;
  function syncPulses() {
    for (const p of pulses) graph.scene().remove(p.mesh);
    pulses = [];
    const f = focus();
    const want = f && f.mode === "play" ? f.pulses || [] : [];
    for (const [i, p] of want.slice(0, 80).entries()) {
      const path = p.nodes.filter((id) => byId.has(id) && nodeVisible(byId.get(id)));
      if (path.length < 2) continue;
      const mesh = new THREE.Mesh(PULSE, material("glow", p.color || "#ffffff", 0.95));
      mesh.renderOrder = 15;
      graph.scene().add(mesh);
      pulses.push({ mesh, path, phase: (i * 0.137) % 1 });
    }
    if (pulses.length && !pulseAnim) pulseAnim = requestAnimationFrame(tickPulses);
  }
  function tickPulses(now) {
    if (!pulses.length) { pulseAnim = null; return; }
    for (const p of pulses) {
      const pts = p.path.map((id) => byId.get(id));
      const seg = [];
      let total = 0;
      for (let i = 1; i < pts.length; i++) {
        const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y, pts[i].z - pts[i - 1].z);
        seg.push(d);
        total += d;
      }
      let at = ((now / 2200 + p.phase) % 1) * total;
      let i = 0;
      while (i < seg.length - 1 && at > seg[i]) { at -= seg[i]; i += 1; }
      const k = seg[i] ? Math.min(1, at / seg[i]) : 0;
      const a = pts[i];
      const b = pts[i + 1];
      p.mesh.position.set(a.x + (b.x - a.x) * k, a.y + (b.y - a.y) * k, a.z + (b.z - a.z) * k);
    }
    pulseAnim = requestAnimationFrame(tickPulses);
  }

  // --- 카메라·토글 ------------------------------------------------------------------------------

  function flyTo(id) {
    const n = byId.get(id);
    if (!n) return;
    const d = 260;
    const len = Math.hypot(n.x, n.z) || 1;
    graph.cameraPosition({ x: n.x + (n.x / len) * d, y: n.y + 160, z: n.z + (n.z / len) * d }, { x: n.x, y: n.y, z: n.z }, 900);
  }

  function setLayer(layer, on) {
    state.layers[layer] = on;
    graph.nodeVisibility((n) => nodeVisible(n));
    refreshLinks();
    applyLabels();
    syncPulses();
  }

  function setLinkType(type, on) {
    state.linkTypes[type] = on;
    refreshLinks();
  }

  function resize() {
    graph.width(el.clientWidth).height(el.clientHeight);
    for (const sp of fixedLabels) rescale(sp);
    for (const { sprite } of shownLabels) rescale(sprite);
  }
  window.addEventListener("resize", resize);
  resize();

  return {
    graph, nodes, links, byId, linkById, incident, timings, THREE,
    select, setView, setOffsets, flyTo, resetCamera, setLayer, setLinkType,
    get selected() { return state.selected; },
    // 점검용: 선택 강조에 그려진 기본 그룹 id → 진한 경로 여부
    get selectedGroups() { return state.selection ? Object.fromEntries(state.selection.groups) : null; },
  };
}

function decorate(scene, sectors) {
  // 층 원판과 층·구역 이름(고정 개수의 스프라이트, 화면 일정 크기)
  const labels = [];
  for (const layer of [1, 2, 3, 4]) {
    const y = LAYER_Y[layer] + (layer === 1 ? BUNDLE_DY / 2 : 0);
    const disc = new THREE.Mesh(
      new THREE.CircleGeometry(layer === 1 ? 240 : 400, 48),
      new THREE.MeshBasicMaterial({ color: "#5b6270", transparent: true, opacity: 0.05, side: THREE.DoubleSide, depthWrite: false }),
    );
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = y - 8;
    scene.add(disc);
    const name = textSprite(LAYER_LABEL[layer], { px: LABEL_PX.layer, color: "#e6e8ec", above: false });
    name.center.set(1, 0.5); // 오른쪽 끝을 원판 왼쪽 가장자리에
    name.position.set(-(layer === 1 ? 250 : 410), y, 0);
    scene.add(name);
    labels.push(name);
  }
  for (const s of sectors) {
    const t = textSprite(s.key, { px: LABEL_PX.sector, color: "#b8bfca", background: "rgba(14,15,18,0.5)", above: false });
    const r = s.radius + 120;
    t.position.set(r * Math.cos(s.angle), s.y + 4, r * Math.sin(s.angle));
    t.userData.sector = true;
    scene.add(t);
    labels.push(t);
  }
  return labels;
}
