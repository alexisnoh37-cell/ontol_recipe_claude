const ROUNDS = [
  {
    kicker: "GAME 1 / 3 · 동물성 식재료",
    title: "먼저, 자주 만나는 식재료부터 알아볼게요",
    description: "고기와 수산물, 달걀과 유제품을 분류해 보세요.",
    complete: "첫 번째 게임을 마쳤어요!",
    next: "이번 결과를 확인한 뒤 콩과 곡물 게임을 시작해요.",
    items: [
      { id: "beef", label: "소고기", icon: "🥩", dish: "🍲", hint: "구이 · 국 · 볶음" },
      { id: "pork", label: "돼지고기", icon: "🐖", dish: "🍖", hint: "삼겹살 · 수육" },
      { id: "chicken", label: "닭고기", icon: "🍗", dish: "🍛", hint: "구이 · 튀김 · 탕" },
      { id: "fish", label: "생선", icon: "🐟", dish: "🍣", hint: "고등어 · 연어 등" },
      { id: "crustacean", label: "갑각류", icon: "🦐🦀", dish: "🍤", hint: "새우 · 게" },
      { id: "shellfish", label: "조개류", icon: "🦪🐚", dish: "🥘", hint: "굴 · 홍합 · 조개" },
      { id: "egg", label: "달걀", icon: "🥚", dish: "🍳", hint: "흰자 · 노른자" },
      { id: "cheese", label: "치즈", icon: "🧀", dish: "🍕", hint: "자연 · 가공 치즈" },
      { id: "butter", label: "버터", icon: "🧈", dish: "🥞", hint: "가염 · 무염" },
      { id: "milk", label: "우유", icon: "🥛", dish: "🍮", hint: "우유 · 두유 아님" },
      { id: "other_dairy", label: "기타 유제품", icon: "🥣🍦", dish: "🍰", hint: "생크림 · 요거트" },
    ],
  },
  {
    kicker: "GAME 2 / 3 · 콩과 곡물",
    title: "매일 먹는 주식과 식물성 단백질이에요",
    description: "콩, 두부, 쌀과 밀로 만든 음식을 분류해 보세요.",
    complete: "두 번째 게임도 끝났어요!",
    next: "이번 결과를 확인한 뒤 마지막 채소와 과일 게임을 시작해요.",
    items: [
      { id: "beans", label: "콩", icon: "🫘", dish: "🥣", hint: "대두 · 검은콩 등" },
      { id: "tofu", label: "두부", icon: "⬜", dish: "🍲", hint: "두부 · 순두부" },
      { id: "rice", label: "쌀 · 밥", icon: "🍚", dish: "🍙", hint: "흰쌀 · 현미 · 잡곡" },
      { id: "flour", label: "밀가루", icon: "🌾", dish: "🥞", hint: "가루 · 반죽 음식" },
      { id: "bread", label: "빵류", icon: "🍞🥐", dish: "🥪", hint: "식빵 · 페이스트리" },
      { id: "noodles", label: "면류", icon: "🍜🍝", dish: "🍜", hint: "국수 · 파스타" },
    ],
  },
  {
    kicker: "GAME 3 / 3 · 채소와 과일",
    title: "마지막은 싱그러운 식재료들이에요",
    description: "채소, 버섯, 해조류와 과일·견과류를 분류해 보세요.",
    complete: "세 번째 게임까지 모두 마쳤어요!",
    next: "마지막 게임 결과를 확인하고 전체 취향 지도를 볼게요.",
    items: [
      { id: "leafy_veg", label: "잎채소", icon: "🥬", dish: "🥗", hint: "배추 · 상추 · 시금치" },
      { id: "root_veg", label: "뿌리채소", icon: "🥕", dish: "🍛", hint: "당근 · 무 · 감자" },
      { id: "mushroom", label: "버섯류", icon: "🍄", dish: "🍲", hint: "표고 · 느타리 등" },
      { id: "seaweed", label: "해조류", icon: "🌿", dish: "🍙", hint: "김 · 미역 · 다시마" },
      { id: "fruit", label: "과일류", icon: "🍎🍑", dish: "🥧", hint: "사과 · 복숭아 등" },
      { id: "nuts", label: "견과류", icon: "🥜🌰", dish: "🍪", hint: "땅콩 · 호두 · 잣" },
    ],
  },
];

const TOTAL_ITEMS = ROUNDS.reduce((sum, round) => sum + round.items.length, 0);
const MAX_VISIBLE = 4;
const SLOT_LAYOUTS = [
  { x: 0.10, y: 0.18 },
  { x: 0.35, y: 0.12 },
  { x: 0.62, y: 0.18 },
  { x: 0.79, y: 0.10 },
  { x: 0.18, y: 0.43 },
  { x: 0.47, y: 0.39 },
  { x: 0.72, y: 0.42 },
];

const MOBILE_SLOT_LAYOUTS = [
  { x: 0.06, y: 0.20 },
  { x: 0.61, y: 0.20 },
  { x: 0.06, y: 0.53 },
  { x: 0.61, y: 0.53 },
];

const BUCKETS = {
  avoid: { label: "못 먹어요", icon: "🗑️", css: "avoid" },
  dislike: { label: "선호하지 않아요", icon: "🧺", css: "dislike" },
  like: { label: "좋아해요", icon: "🍽️", css: "like" },
};

const state = {
  roundIndex: 0,
  queue: [],
  visible: new Map(),
  selectedId: null,
  results: { avoid: [], dislike: [], like: [], skipped: [] },
  cardOrigins: new Map(),
  cameraStream: null,
  cameraActive: false,
  gestureRecognizer: null,
  lastVideoTime: -1,
  recognitionFrame: 0,
  handGrabbedId: null,
  hoverStartedAt: 0,
  releaseStartedAt: 0,
  lastHoveredId: null,
  toastTimer: 0,
};

const dom = {
  stage: document.querySelector("#gameStage"),
  video: document.querySelector("#cameraVideo"),
  canvas: document.querySelector("#handCanvas"),
  cards: document.querySelector("#cardsLayer"),
  cursor: document.querySelector("#palmCursor"),
  cursorLabel: document.querySelector("#cursorLabel"),
  gestureIcon: document.querySelector("#gestureIcon"),
  gestureText: document.querySelector("#gestureText"),
  cameraButton: document.querySelector("#cameraButton"),
  cameraStatus: document.querySelector("#cameraStatus"),
  skipButton: document.querySelector("#skipButton"),
  roundKicker: document.querySelector("#roundKicker"),
  roundTitle: document.querySelector("#roundTitle"),
  roundDescription: document.querySelector("#roundDescription"),
  progressText: document.querySelector("#progressText"),
  overallText: document.querySelector("#overallText"),
  progressBar: document.querySelector("#progressBar"),
  roundDots: [...document.querySelectorAll("#roundDots span")],
  sortedCount: document.querySelector("#sortedCount"),
  trays: {
    avoid: document.querySelector("#avoidTray"),
    dislike: document.querySelector("#dislikeTray"),
    like: document.querySelector("#likeTray"),
  },
  zones: [...document.querySelectorAll(".drop-zone")],
  intro: document.querySelector("#introDialog"),
  mouseStart: document.querySelector("#mouseStartButton"),
  cameraStart: document.querySelector("#cameraStartButton"),
  roundDialog: document.querySelector("#roundDialog"),
  roundCompleteKicker: document.querySelector("#roundCompleteKicker"),
  roundCompleteTitle: document.querySelector("#roundCompleteTitle"),
  roundCompleteDescription: document.querySelector("#roundCompleteDescription"),
  roundSummary: document.querySelector("#roundSummary"),
  nextRound: document.querySelector("#nextRoundButton"),
  resultDialog: document.querySelector("#resultDialog"),
  resultCount: document.querySelector("#resultCount"),
  resultColumns: document.querySelector("#resultColumns"),
  followupNotice: document.querySelector("#followupNotice"),
  restart: document.querySelector("#restartButton"),
  copy: document.querySelector("#copyButton"),
  detail: document.querySelector("#detailButton"),
  help: document.querySelector("#helpDialog"),
  helpButton: document.querySelector("#helpButton"),
  helpClose: document.querySelector("#helpCloseButton"),
  toast: document.querySelector("#toast"),
};

function shuffled(items) {
  const output = [...items];
  for (let index = output.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(Math.random() * (index + 1));
    [output[index], output[swap]] = [output[swap], output[index]];
  }
  return output;
}

function allItems() {
  return ROUNDS.flatMap((round) => round.items);
}

function findItem(id) {
  return allItems().find((item) => item.id === id);
}

function sortedTotal() {
  return Object.values(state.results).reduce((sum, items) => sum + items.length, 0);
}

function classifiedTotal() {
  return state.results.avoid.length + state.results.dislike.length + state.results.like.length;
}

function resultsForRound(index) {
  const ids = new Set(ROUNDS[index].items.map((item) => item.id));
  return Object.fromEntries(
    Object.entries(state.results).map(([key, items]) => [key, items.filter((item) => ids.has(item.id))]),
  );
}

function roundSortedTotal(index = state.roundIndex) {
  return Object.values(resultsForRound(index)).reduce((sum, items) => sum + items.length, 0);
}

function updateProgress() {
  const round = ROUNDS[state.roundIndex];
  const roundDone = roundSortedTotal();
  dom.progressText.textContent = `${roundDone} / ${round.items.length}`;
  dom.overallText.textContent = `전체 ${sortedTotal()} / ${TOTAL_ITEMS}`;
  dom.progressBar.style.width = `${(roundDone / round.items.length) * 100}%`;
  dom.sortedCount.textContent = classifiedTotal();

  dom.roundDots.forEach((dot, index) => {
    dot.classList.toggle("active", index === state.roundIndex);
    dot.classList.toggle("done", index < state.roundIndex);
  });
}

function updateTrays() {
  for (const key of ["avoid", "dislike", "like"]) {
    const tray = dom.trays[key];
    const items = state.results[key];
    tray.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("span");
      empty.className = "empty-copy";
      empty.textContent = "아직 없어요";
      tray.append(empty);
      continue;
    }
    for (const item of items) {
      const chip = document.createElement("span");
      chip.className = "mini-chip";
      chip.textContent = `${item.icon} ${item.label}`;
      tray.append(chip);
    }
  }
}

function showToast(message) {
  clearTimeout(state.toastTimer);
  dom.toast.textContent = message;
  dom.toast.classList.add("show");
  state.toastTimer = window.setTimeout(() => dom.toast.classList.remove("show"), 1800);
}

function setRound(index) {
  state.roundIndex = index;
  state.visible.clear();
  state.cardOrigins.clear();
  state.selectedId = null;
  state.handGrabbedId = null;
  dom.cards.replaceChildren();

  const round = ROUNDS[index];
  state.queue = shuffled(round.items);
  dom.roundKicker.textContent = round.kicker;
  dom.roundTitle.textContent = round.title;
  dom.roundDescription.textContent = round.description;
  updateProgress();
  fillVisibleCards();
}

function availableSlots() {
  const used = new Set([...state.visible.values()].map((value) => value.slot));
  return shuffled(slotLayouts().map((_, index) => index).filter((index) => !used.has(index)));
}

function slotLayouts() {
  return window.matchMedia("(max-width: 720px)").matches ? MOBILE_SLOT_LAYOUTS : SLOT_LAYOUTS;
}

function fillVisibleCards() {
  const freeSlots = availableSlots();
  while (state.visible.size < MAX_VISIBLE && state.queue.length && freeSlots.length) {
    const item = state.queue.shift();
    const slot = freeSlots.shift();
    state.visible.set(item.id, { item, slot });
    createCard(item, slot);
  }

  if (!state.visible.size && !state.queue.length) {
    window.setTimeout(showRoundComplete, 350);
  }
}

function createCard(item, slotIndex) {
  const card = document.createElement("article");
  card.className = "ingredient-card entering";
  card.dataset.id = item.id;
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-label", `${item.label} 카드. 끌어서 분류하세요.`);
  card.innerHTML = `
    <span class="ingredient-icon" aria-hidden="true">${item.icon}</span>
    <strong>${item.label}</strong>
    <small>${item.hint}</small>
  `;

  const position = slotLayouts()[slotIndex];
  card.style.left = `${position.x * 100}%`;
  card.style.top = `${position.y * 100}%`;
  state.cardOrigins.set(item.id, { left: card.style.left, top: card.style.top });

  card.addEventListener("pointerdown", onCardPointerDown);
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectCard(item.id);
    }
  });
  dom.cards.append(card);
  window.setTimeout(() => card.classList.remove("entering"), 460);
}

function selectCard(id) {
  const card = cardElement(id);
  if (!card) return;
  document.querySelectorAll(".ingredient-card.selected").forEach((element) => element.classList.remove("selected"));
  state.selectedId = id;
  card.classList.add("selected");
  dom.skipButton.disabled = false;
}

function clearSelection({ snapBack = false } = {}) {
  if (state.selectedId) {
    const card = cardElement(state.selectedId);
    if (card) {
      card.classList.remove("selected");
      if (snapBack) snapCardBack(state.selectedId);
    }
  }
  state.selectedId = null;
  state.handGrabbedId = null;
  dom.skipButton.disabled = true;
  clearZoneHighlights();
}

function cardElement(id) {
  return dom.cards.querySelector(`[data-id="${id}"]`);
}

function snapCardBack(id) {
  const card = cardElement(id);
  const origin = state.cardOrigins.get(id);
  if (!card || !origin) return;
  card.style.left = origin.left;
  card.style.top = origin.top;
}

function positionCard(id, stageX, stageY) {
  const card = cardElement(id);
  if (!card) return;
  const cardsRect = dom.cards.getBoundingClientRect();
  const left = stageX - cardsRect.left - card.offsetWidth / 2;
  const top = stageY - cardsRect.top - card.offsetHeight / 2;
  card.style.left = `${left}px`;
  card.style.top = `${top}px`;
}

function zoneAt(clientX, clientY) {
  return dom.zones.find((zone) => {
    const rect = zone.getBoundingClientRect();
    return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
  });
}

function cardAt(clientX, clientY) {
  return [...dom.cards.querySelectorAll(".ingredient-card")].reverse().find((card) => {
    const rect = card.getBoundingClientRect();
    return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
  });
}

function highlightZone(clientX, clientY) {
  const target = zoneAt(clientX, clientY);
  dom.zones.forEach((zone) => zone.classList.toggle("drag-over", zone === target));
  return target;
}

function clearZoneHighlights() {
  dom.zones.forEach((zone) => zone.classList.remove("drag-over"));
}

function playBucketReaction(bucket, item) {
  const zone = dom.zones.find((candidate) => candidate.dataset.bucket === bucket);
  const scene = zone?.querySelector(".zone-scene");
  if (!zone || !scene) return;

  zone.classList.remove("reacting");
  void zone.offsetWidth;
  zone.classList.add("reacting");

  const effect = document.createElement("span");
  effect.className = `bucket-effect ${bucket}-effect`;
  if (bucket === "avoid") {
    effect.innerHTML = `<b>${item.icon}</b><i>퐁!</i>`;
  } else if (bucket === "dislike") {
    effect.innerHTML = `<b>${item.icon}</b><i>보관</i>`;
  } else {
    effect.innerHTML = `<b class="raw-food">${item.icon}</b><i>✦</i><b class="cooked-food">${item.dish}</b>`;
  }
  scene.append(effect);

  window.setTimeout(() => {
    effect.remove();
    zone.classList.remove("reacting");
  }, 900);
}

function classify(id, bucket) {
  const entry = state.visible.get(id);
  if (!entry || !BUCKETS[bucket]) return;
  const card = cardElement(id);
  const item = entry.item;
  playBucketReaction(bucket, item);
  state.results[bucket].push(item);
  state.visible.delete(id);
  state.cardOrigins.delete(id);
  clearSelection();
  if (card) {
    card.classList.add("leaving");
    window.setTimeout(() => {
      card.remove();
      fillVisibleCards();
    }, 720);
  } else {
    fillVisibleCards();
  }
  updateProgress();
  updateTrays();
  showToast(`${item.label} → ${BUCKETS[bucket].label}`);
}

function skipSelected() {
  const id = state.selectedId;
  const entry = state.visible.get(id);
  if (!entry) return;
  const card = cardElement(id);
  state.results.skipped.push(entry.item);
  state.visible.delete(id);
  state.cardOrigins.delete(id);
  clearSelection();
  card?.classList.add("leaving");
  window.setTimeout(() => {
    card?.remove();
    fillVisibleCards();
  }, 250);
  updateProgress();
  showToast(`${entry.item.label}은(는) 보류했어요`);
}

function onCardPointerDown(event) {
  if (event.pointerType === "touch") event.preventDefault();
  const card = event.currentTarget;
  const id = card.dataset.id;
  selectCard(id);
  card.setPointerCapture?.(event.pointerId);

  const move = (moveEvent) => {
    positionCard(id, moveEvent.clientX, moveEvent.clientY);
    highlightZone(moveEvent.clientX, moveEvent.clientY);
  };

  const up = (upEvent) => {
    card.removeEventListener("pointermove", move);
    card.removeEventListener("pointerup", up);
    card.removeEventListener("pointercancel", cancel);
    const zone = zoneAt(upEvent.clientX, upEvent.clientY);
    if (zone) classify(id, zone.dataset.bucket);
    else clearSelection({ snapBack: true });
  };

  const cancel = () => {
    card.removeEventListener("pointermove", move);
    card.removeEventListener("pointerup", up);
    card.removeEventListener("pointercancel", cancel);
    clearSelection({ snapBack: true });
  };

  card.addEventListener("pointermove", move);
  card.addEventListener("pointerup", up);
  card.addEventListener("pointercancel", cancel);
}

function showRoundComplete() {
  const round = ROUNDS[state.roundIndex];
  const roundResults = resultsForRound(state.roundIndex);
  dom.roundCompleteKicker.textContent = `GAME ${state.roundIndex + 1} / ${ROUNDS.length} COMPLETE`;
  dom.roundCompleteTitle.textContent = round.complete;
  dom.roundCompleteDescription.textContent = round.next;
  dom.roundSummary.innerHTML = ["avoid", "dislike", "like", "skipped"].map((key) => {
    const labels = {
      avoid: ["🗑️", "버림"],
      dislike: ["🧺", "보관"],
      like: ["🍽️", "요리"],
      skipped: ["⏸️", "보류"],
    };
    const [icon, label] = labels[key];
    return `<span class="round-summary-item ${key}"><b>${icon}</b><strong>${roundResults[key].length}</strong><small>${label}</small></span>`;
  }).join("");
  dom.nextRound.textContent = state.roundIndex === ROUNDS.length - 1
    ? "전체 결과 확인하기"
    : `${state.roundIndex + 2}번째 게임 시작`;
  if (!dom.roundDialog.open) dom.roundDialog.showModal();
}

function continueRound() {
  dom.roundDialog.close();
  if (state.roundIndex === ROUNDS.length - 1) {
    showResults();
    return;
  }
  setRound(state.roundIndex + 1);
}

function showResults() {
  const columns = ["avoid", "dislike", "like"].map((key) => {
    const meta = BUCKETS[key];
    const items = state.results[key];
    const chips = items.length
      ? items.map((item) => `<span class="result-item">${item.icon} ${item.label}</span>`).join("")
      : '<span class="empty-copy">선택한 재료가 없어요</span>';
    return `
      <section class="result-column ${meta.css}">
        <h3>${meta.icon} ${meta.label} · ${items.length}</h3>
        <div class="result-items">${chips}</div>
      </section>
    `;
  }).join("");

  dom.resultCount.textContent = classifiedTotal();
  dom.resultColumns.innerHTML = columns;
  dom.followupNotice.innerHTML = state.results.avoid.length
    ? `<strong>다음 단계가 필요해요.</strong> ${state.results.avoid.map((item) => item.label).join(", ")} 항목은 알레르기인지, 절대 먹지 않는 것인지 상세 입력에서 확인해야 합니다.`
    : "못 먹는 것으로 분류한 항목이 없습니다. 필요하다면 상세 입력에서 알레르기를 별도로 확인해 주세요.";
  dom.resultDialog.showModal();
}

function resetGame() {
  for (const key of Object.keys(state.results)) state.results[key] = [];
  state.roundIndex = 0;
  dom.resultDialog.close();
  updateTrays();
  setRound(0);
}

function exportResult() {
  const payload = {
    version: "ingredient-sort-poc/2",
    completedAt: new Date().toISOString(),
    games: ROUNDS.map((round, index) => ({
      game: index + 1,
      title: round.kicker,
      results: Object.fromEntries(
        Object.entries(resultsForRound(index)).map(([key, items]) => [key, items.map(({ id, label }) => ({ id, label }))]),
      ),
    })),
    results: Object.fromEntries(
      Object.entries(state.results).map(([key, items]) => [key, items.map(({ id, label }) => ({ id, label }))]),
    ),
  };
  return payload;
}

async function copyResult() {
  try {
    await navigator.clipboard.writeText(JSON.stringify(exportResult(), null, 2));
    showToast("결과 JSON을 복사했어요");
  } catch {
    showToast("브라우저에서 복사를 허용하지 않았어요");
  }
}

function showDetailPlaceholder() {
  const avoid = state.results.avoid;
  if (!avoid.length) {
    showToast("상세 입력 화면은 다음 POC 단계에서 연결합니다");
    return;
  }
  showToast(`${avoid.length}개 못 먹는 항목의 상세 확인이 필요해요`);
}

async function startCamera() {
  if (state.cameraActive) {
    stopCamera();
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    showToast("이 브라우저에서는 카메라를 사용할 수 없어요");
    return;
  }

  try {
    setCameraStatus("loading", "손 인식 모델 준비 중…");
    await ensureGestureRecognizer();
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
      audio: false,
    });
    state.cameraStream = stream;
    dom.video.srcObject = stream;
    await dom.video.play();
    state.cameraActive = true;
    dom.stage.classList.add("camera-active");
    dom.cursor.classList.add("visible");
    setCameraStatus("on", "카메라 · 손 인식 중");
    dom.cameraButton.innerHTML = "<span>⏹️</span> 카메라 끄기";
    dom.gestureIcon.textContent = "🖐️";
    dom.gestureText.textContent = "손바닥을 보여주세요";
    state.recognitionFrame = requestAnimationFrame(recognizeFrame);
  } catch (error) {
    console.error(error);
    stopCamera();
    setCameraStatus("off", "카메라를 시작하지 못했어요");
    showToast("카메라 권한과 인터넷 연결을 확인해 주세요");
  }
}

function stopCamera() {
  if (state.recognitionFrame) cancelAnimationFrame(state.recognitionFrame);
  state.cameraStream?.getTracks().forEach((track) => track.stop());
  state.cameraStream = null;
  state.cameraActive = false;
  state.lastVideoTime = -1;
  dom.video.srcObject = null;
  dom.stage.classList.remove("camera-active");
  dom.cursor.classList.remove("visible", "grabbing");
  clearHandCanvas();
  clearSelection({ snapBack: true });
  setCameraStatus("off", "마우스 체험 모드");
  dom.cameraButton.innerHTML = "<span>📷</span> 카메라 켜기";
  dom.gestureIcon.textContent = "🖱️";
  dom.gestureText.textContent = "카드를 끌어서 분류 칸에 놓아보세요";
}

function setCameraStatus(mode, text) {
  dom.cameraStatus.classList.toggle("status-on", mode === "on");
  dom.cameraStatus.classList.toggle("status-off", mode !== "on");
  dom.cameraStatus.querySelector("span:last-child").textContent = text;
}

async function ensureGestureRecognizer() {
  if (state.gestureRecognizer) return;
  const visionModule = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm");
  const { FilesetResolver, GestureRecognizer } = visionModule;
  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm",
  );
  state.gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numHands: 1,
    minHandDetectionConfidence: 0.55,
    minHandPresenceConfidence: 0.55,
    minTrackingConfidence: 0.55,
    cannedGesturesClassifierOptions: { scoreThreshold: 0.55 },
  });
}

async function recognizeFrame() {
  if (!state.cameraActive || !state.gestureRecognizer) return;
  if (dom.video.readyState >= 2 && dom.video.currentTime !== state.lastVideoTime) {
    state.lastVideoTime = dom.video.currentTime;
    const result = state.gestureRecognizer.recognizeForVideo(dom.video, performance.now());
    handleGestureResult(result);
  }
  state.recognitionFrame = requestAnimationFrame(recognizeFrame);
}

function handleGestureResult(result) {
  clearHandCanvas();
  const landmarks = result.landmarks?.[0];
  if (!landmarks) {
    dom.cursor.classList.remove("visible");
    dom.gestureText.textContent = "손바닥을 카메라에 보여주세요";
    clearHoverState();
    return;
  }

  dom.cursor.classList.add("visible");
  drawLandmarks(landmarks);
  const palm = palmCenter(landmarks);
  const stageRect = dom.stage.getBoundingClientRect();
  const clientX = stageRect.left + palm.x * stageRect.width;
  const clientY = stageRect.top + palm.y * stageRect.height;
  dom.cursor.style.left = `${palm.x * 100}%`;
  dom.cursor.style.top = `${palm.y * 100}%`;

  const gesture = result.gestures?.[0]?.[0];
  const gestureName = gesture?.categoryName ?? "None";
  const closed = gestureName === "Closed_Fist" && gesture.score >= 0.55;
  const open = gestureName === "Open_Palm" && gesture.score >= 0.5;

  if (!state.handGrabbedId) {
    const hoveredCard = cardAt(clientX, clientY);
    setHoveredCard(hoveredCard?.dataset.id ?? null);
    dom.cursor.classList.remove("grabbing");
    dom.cursorLabel.textContent = closed ? "잡는 중…" : "손바닥";

    if (closed && hoveredCard) {
      const id = hoveredCard.dataset.id;
      if (state.lastHoveredId !== id) {
        state.lastHoveredId = id;
        state.hoverStartedAt = performance.now();
      }
      if (performance.now() - state.hoverStartedAt > 220) {
        state.handGrabbedId = id;
        selectCard(id);
        dom.gestureText.textContent = "좋아요! 원하는 분류 칸으로 옮겨보세요";
      }
    } else {
      state.hoverStartedAt = 0;
    }
    return;
  }

  const id = state.handGrabbedId;
  dom.cursor.classList.add("grabbing");
  dom.cursorLabel.textContent = closed ? "잡았어요" : "손을 펴서 놓기";
  positionCard(id, clientX, clientY);
  const zone = highlightZone(clientX, clientY);

  if (open && zone) {
    if (!state.releaseStartedAt) state.releaseStartedAt = performance.now();
    if (performance.now() - state.releaseStartedAt > 260) {
      classify(id, zone.dataset.bucket);
      state.releaseStartedAt = 0;
      dom.gestureText.textContent = "다음 재료를 골라볼까요?";
    }
  } else {
    state.releaseStartedAt = 0;
  }
}

function palmCenter(landmarks) {
  const palmIndexes = [0, 5, 9, 13, 17];
  const center = palmIndexes.reduce((sum, index) => ({
    x: sum.x + (1 - landmarks[index].x),
    y: sum.y + landmarks[index].y,
  }), { x: 0, y: 0 });
  return { x: center.x / palmIndexes.length, y: center.y / palmIndexes.length };
}

function drawLandmarks(landmarks) {
  const rect = dom.stage.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  if (dom.canvas.width !== Math.round(rect.width * dpr) || dom.canvas.height !== Math.round(rect.height * dpr)) {
    dom.canvas.width = Math.round(rect.width * dpr);
    dom.canvas.height = Math.round(rect.height * dpr);
  }
  const context = dom.canvas.getContext("2d");
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.fillStyle = "rgba(216, 255, 99, .9)";
  for (const point of landmarks) {
    context.beginPath();
    context.arc((1 - point.x) * rect.width, point.y * rect.height, 2.2, 0, Math.PI * 2);
    context.fill();
  }
}

function clearHandCanvas() {
  const context = dom.canvas.getContext("2d");
  context.clearRect(0, 0, dom.canvas.width, dom.canvas.height);
}

function setHoveredCard(id) {
  document.querySelectorAll(".ingredient-card.hovered").forEach((card) => card.classList.remove("hovered"));
  if (id) cardElement(id)?.classList.add("hovered");
  if (id !== state.lastHoveredId) {
    state.lastHoveredId = id;
    state.hoverStartedAt = performance.now();
  }
}

function clearHoverState() {
  setHoveredCard(null);
  state.lastHoveredId = null;
  state.hoverStartedAt = 0;
}

function beginMouseMode() {
  dom.intro.close();
  setRound(0);
}

async function beginCameraMode() {
  dom.intro.close();
  setRound(0);
  await startCamera();
}

function bindEvents() {
  dom.mouseStart.addEventListener("click", beginMouseMode);
  dom.cameraStart.addEventListener("click", beginCameraMode);
  dom.cameraButton.addEventListener("click", startCamera);
  dom.skipButton.addEventListener("click", skipSelected);
  dom.nextRound.addEventListener("click", continueRound);
  dom.restart.addEventListener("click", resetGame);
  dom.copy.addEventListener("click", copyResult);
  dom.detail.addEventListener("click", showDetailPlaceholder);
  dom.helpButton.addEventListener("click", () => dom.help.showModal());
  dom.helpClose.addEventListener("click", () => dom.help.close());
  dom.zones.forEach((zone) => zone.addEventListener("click", () => {
    if (state.selectedId) classify(state.selectedId, zone.dataset.bucket);
  }));
  window.addEventListener("beforeunload", stopCamera);
}

bindEvents();
updateProgress();
updateTrays();
dom.intro.showModal();
