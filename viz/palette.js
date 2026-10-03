// 층 배치와 색 규칙 (docs/plan.md 부록 D-1·D-2). 판정과 무관한 표시 값만 둔다.

export const LAYER_Y = { 1: -540, 2: -180, 3: 180, 4: 540 }; // 층 간격 360(35도로 내려다볼 때 층이 덜 겹치게)
export const BUNDLE_DY = -35; // 묶음 그룹은 기본 그룹보다 조금 아래

export const LAYER_LABEL = { 1: "1층 알레르기 그룹", 2: "2층 원천 재료·분류", 3: "3층 가공품", 4: "4층 레시피" };

export const NODE_COLOR = {
  official: "#e5484d", // 법정 표시 대상 기본 그룹
  custom: "#f76b15", // 자체 기본 그룹(테두리만)
  bundle: "#8e4ec6", // 묶음 그룹
  raw: "#46a758", // 원천 재료
  concept: "#8da38d", // 분류(concept, 와이어프레임)
  processed: "#0090ff", // 가공품(derived_from 있음)
  recipe: "#e8dcc0",
  lowConfidence: "#f5d90a", // confidence: low 고리
};

export const LINK_COLOR = {
  is_a: "#9ba1a6",
  derived_from: "#5eb1ef",
  allergen: "#ff6369",
  bundle_member: "#9e8cfc",
  main: "#ffb224",
  sub: "#12a594",
  seasoning: "#b4a7d6",
  garnish: "#e93d82",
};

export const LINK_LABEL = {
  is_a: "is_a (하위 → 상위)",
  derived_from: "derived_from (가공품 → 원천)",
  allergen: "알레르기 지정 (재료 → 그룹)",
  bundle_member: "묶음 구성 (묶음 → 기본 그룹)",
  main: "레시피-재료: 주재료",
  sub: "레시피-재료: 부재료",
  seasoning: "레시피-재료: 양념",
  garnish: "레시피-재료: 고명",
};

export const GROUP_CATEGORY_LABEL = { official: "법정 표시 대상", custom: "자체 그룹", bundle: "묶음 그룹" };
export const ROLE_LABEL = { main: "주재료", sub: "부재료", seasoning: "양념", garnish: "고명" };

// 링크 투명도. linkAlpha = 강조했을 때의 원래 진하기, linkRestAlpha = 아무것도 선택하지 않았을 때(배경)
export function linkAlpha(link) {
  if (link.type === "uses") return link.optional ? 0.45 : 0.9;
  if (link.certainty === "possible") return 0.55;
  if (link.type === "is_a" || link.type === "bundle_member") return 0.75;
  return 0.9;
}

export function linkRestAlpha(link) {
  if (link.type === "uses") return link.optional ? 0.2 : 0.4;
  if (link.type === "is_a" || link.type === "bundle_member") return 0.2;
  return link.certainty === "possible" ? 0.09 : 0.15; // derived_from·알레르기 지정
}

// 재생(부록 D-5) 색: 제외 사유별(알레르기 빨강, 절대 불선호 주황, 나머지 회색)
export const REASON_COLOR = {
  allergen: "#ff4d55",
  unmapped_ingredient: "#c2414b",
  hard_dislike_ingredient: "#ff8b3e",
  hard_dislike_cuisine: "#8b8d98",
  spicy_limit: "#8b8d98",
  equipment: "#8b8d98",
  time: "#8b8d98",
};
export const REASON_SHORT = {
  allergen: "알레르기",
  unmapped_ingredient: "미매칭 재료",
  hard_dislike_ingredient: "절대 불선호 재료",
  hard_dislike_cuisine: "절대 불선호 음식 종류",
  spicy_limit: "매운맛 한도",
  equipment: "조리기구",
  time: "조리시간",
};
export const PLAY_COLOR = { owned: "#3dd68c", staple: "#7fb59a", ancestor: "#a4e8c4", candidate: "#ffe08a", pass: "#e8dcc0", rank: "#ffb224", moved: "#ff8b3e" };

export function linkBaseColor(link) {
  return link.type === "uses" ? LINK_COLOR[link.role] : LINK_COLOR[link.type];
}

export function rgba(hex, alpha) {
  const v = parseInt(hex.slice(1), 16);
  return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${alpha.toFixed(3)})`;
}
