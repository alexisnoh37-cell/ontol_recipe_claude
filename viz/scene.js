// 3D 장면: 층 배치, 노드·간선 표현, 강조(재질만 변경). 판정하지 않는다(docs/plan.md 부록 D).
//
// 성능 규칙(부록 D-6, 목표 레시피 1천 개)
//   - y는 층으로 고정(fy), x·z만 warmup 동안 계산하고 cooldownTicks(0)으로 멈춘다.
//   - 레시피-재료 간선은 기본 숨김. 숨긴 간선은 three 객체를 만들지 않는다(3d-force-graph가 visible만 생성).
//   - 강조는 노드 메시의 재질만 바꾼다(graphData 재설정 금지). 재질은 (색, 투명도)별로 공유한다.
//   - 텍스트 스프라이트는 층·구역 이름과 선택한 노드 하나만.

import ForceGraph3D from "https://cdn.jsdelivr.net/npm/3d-force-graph@1.80.1/+esm";
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.186.1/+esm";

import { BUNDLE_DY, LAYER_LABEL, LAYER_Y, NODE_COLOR, linkAlpha, linkBaseColor, rgba } from "./palette.js";

const DIM = 0.07; // 강조 밖 노드 투명도
const LINK_DIM = 0.04;
const RADIUS = { group: 120, bundle: 190, ingredient: 270, recipe: 230 };

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
    sectors.push({ key, angle: center, y });
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
    ...sectorLayout(ing3, (n) => n.category || "기타", RADIUS.ingredient * 0.8, LAYER_Y[3]),
    ...sectorLayout(recipes, (n) => n.cuisine || "기타", RADIUS.recipe, LAYER_Y[4]),
  ];
}

function anchorForce() {
  // 각자 구역 중심 쪽으로 약하게 당긴다(x·z만). 레시피는 재료 간선이 더 세게 당기도록 약하게.
  let nodes = [];
  const force = (alpha) => {
    for (const n of nodes) {
      if (n.ax === undefined || n.fx !== undefined) continue;
      const k = (n.kind === "recipe" ? 0.04 : 0.09) * alpha;
      n.vx += (n.ax - n.x) * k;
      n.vz += (n.az - n.z) * k;
    }
  };
  force.initialize = (ns) => { nodes = ns; };
  return force;
}

function linkStrength(l) {
  if (l.type === "uses") return l.role === "main" ? 0.12 : 0.02;
  if (l.type === "is_a" || l.type === "derived_from") return 0.3;
  if (l.type === "allergen") return 0.04;
  return 0;
}

// --- 그리기 도구 ---------------------------------------------------------------------------------

const GEOMETRY = {
  sphere: new THREE.SphereGeometry(4, 8, 6),
  icosa: new THREE.IcosahedronGeometry(4.6, 0),
  box: new THREE.BoxGeometry(9, 9, 9),
  octa: new THREE.OctahedronGeometry(11, 0),
  cylinder: new THREE.CylinderGeometry(5.5, 5.5, 2.6, 10),
};
const EDGES = { box: new THREE.EdgesGeometry(GEOMETRY.box), octa: new THREE.EdgesGeometry(GEOMETRY.octa) };
const RING = new THREE.TorusGeometry(7, 0.5, 4, 16);

const materials = new Map();
function material(kind, color, opacity) {
  const key = `${kind}|${color}|${opacity.toFixed(3)}`;
  let m = materials.get(key);
  if (!m) {
    const opts = { color, transparent: opacity < 1, opacity, depthWrite: opacity >= 1 };
    m = kind === "line" ? new THREE.LineBasicMaterial(opts)
      : kind === "wire" ? new THREE.MeshBasicMaterial({ ...opts, wireframe: true })
      : new THREE.MeshLambertMaterial(opts);
    materials.set(key, m);
  }
  return m;
}

export function textSprite(text, { size = 14, color = "#e6e8ec", background = "rgba(14,15,18,0.75)" } = {}) {
  const scale = 4; // 선명도
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const font = `600 ${size * scale}px "Malgun Gothic", "Apple SD Gothic Neo", sans-serif`;
  ctx.font = font;
  const pad = 6 * scale;
  canvas.width = Math.ceil(ctx.measureText(text).width) + pad * 2;
  canvas.height = size * scale + pad * 2;
  ctx.font = font;
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = color;
  ctx.textBaseline = "middle";
  ctx.fillText(text, pad, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthWrite: false, transparent: true }));
  const h = size * 0.75;
  sprite.scale.set((h * canvas.width) / canvas.height, h, 1);
  sprite.renderOrder = 20;
  return sprite;
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
    focus: null, // { nodes: Set<id>, links: Set<link> }
    selected: null,
  };
  const objects = new Map(); // node id → THREE.Mesh

  function nodeVisible(n) {
    return state.layers[n.layer];
  }
  function linkVisible(l) {
    const a = byId.get(l.s);
    const b = byId.get(l.t);
    if (!nodeVisible(a) || !nodeVisible(b)) return false;
    return state.linkTypes[l.type] || (state.focus !== null && state.focus.links.has(l));
  }
  function linkColor(l) {
    let alpha = linkAlpha(l);
    if (state.focus) alpha = state.focus.links.has(l) ? Math.max(alpha, 0.8) : LINK_DIM;
    return rgba(linkBaseColor(l), alpha);
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
    const dim = state.focus && !state.focus.nodes.has(n.id);
    const opacity = dim ? DIM : 1;
    mesh.material = st.hollow ? material("solid", st.color, opacity * 0.18)
      : material(st.wire ? "wire" : "solid", st.color, opacity);
    for (const child of mesh.children) {
      child.material = child.userData.ring ? material("solid", NODE_COLOR.lowConfidence, opacity * 0.8)
        : material("line", st.color, opacity);
    }
    const s = state.selected === n.id ? 1.6 : 1;
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
    .strength(linkStrength);

  const tData = performance.now();
  graph.graphData({ nodes, links });
  const tLayout = performance.now();
  decorate(graph.scene(), sectors);
  const timings = { graphData: tLayout - tData, decorate: performance.now() - tLayout };
  graph.cameraPosition({ x: 0, y: 820, z: 1300 }, { x: 0, y: -20, z: 0 });

  function refreshLinks() {
    graph.linkVisibility((l) => linkVisible(l)).linkColor((l) => linkColor(l));
  }

  // --- 강조 ------------------------------------------------------------------------------------

  let label = null;
  function select(id) {
    state.selected = id;
    if (label) {
      graph.scene().remove(label);
      label.material.map.dispose();
      label.material.dispose();
      label = null;
    }
    if (id === null) {
      state.focus = null;
    } else {
      const ls = new Set(incident.get(id));
      const ns = new Set([id]);
      for (const l of ls) {
        ns.add(l.s);
        ns.add(l.t);
      }
      state.focus = { nodes: ns, links: ls };
      const n = byId.get(id);
      label = textSprite(n.name, { size: 18 });
      label.position.set(n.x, n.y + 14, n.z);
      graph.scene().add(label);
    }
    for (const n of nodes) paintNode(n);
    refreshLinks();
    onSelect?.(id === null ? null : byId.get(id));
  }

  function flyTo(id) {
    const n = byId.get(id);
    if (!n) return;
    const d = 260;
    const len = Math.hypot(n.x, n.z) || 1;
    graph.cameraPosition({ x: n.x + (n.x / len) * d, y: n.y + 120, z: n.z + (n.z / len) * d }, { x: n.x, y: n.y, z: n.z }, 900);
  }

  function setLayer(layer, on) {
    state.layers[layer] = on;
    graph.nodeVisibility((n) => nodeVisible(n));
    refreshLinks();
  }

  function setLinkType(type, on) {
    state.linkTypes[type] = on;
    refreshLinks();
  }

  function resize() {
    graph.width(el.clientWidth).height(el.clientHeight);
  }
  window.addEventListener("resize", resize);
  resize();

  return { graph, nodes, links, byId, linkById, incident, select, flyTo, setLayer, setLinkType, timings, THREE };
}

function decorate(scene, sectors) {
  // 층 원판과 층·구역 이름(고정 개수의 스프라이트)
  for (const layer of [1, 2, 3, 4]) {
    const y = LAYER_Y[layer] + (layer === 1 ? BUNDLE_DY / 2 : 0);
    const disc = new THREE.Mesh(
      new THREE.CircleGeometry(layer === 1 ? 240 : 380, 48),
      new THREE.MeshBasicMaterial({ color: "#5b6270", transparent: true, opacity: 0.05, side: THREE.DoubleSide, depthWrite: false }),
    );
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = y - 8;
    scene.add(disc);
    const name = textSprite(LAYER_LABEL[layer], { size: 30, color: "#c8cdd6" });
    name.position.set(-(layer === 1 ? 330 : 470), y, 0);
    scene.add(name);
  }
  for (const s of sectors) {
    const t = textSprite(s.key, { size: 16, color: "#9aa1ad", background: "rgba(14,15,18,0.4)" });
    const r = 400;
    t.position.set(r * Math.cos(s.angle), s.y + 4, r * Math.sin(s.angle));
    scene.add(t);
  }
}
