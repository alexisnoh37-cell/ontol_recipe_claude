(() => {
  "use strict";

  const data = window.RECIPE_DATA;
  const recipes = data?.recipes || [];
  const state = { query: "", cuisine: "전체", difficulty: "all", time: "all", sort: "recommended", visible: 18 };
  const cuisineColors = { 한식: "#173d2d", 양식: "#ef6c3b", 일식: "#e7ad3b", 중식: "#6e9e9b", 기타: "#a79b8a" };
  const difficultyNames = { 1: "쉬움", 2: "보통", 3: "어려움" };
  const tasteNames = { spicy: "매운맛", salty: "짠맛", sweet: "단맛", sour: "신맛", umami: "감칠맛", savory: "고소함" };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const formatAmount = (value) => {
    if (value === null || value === undefined) return "";
    const fractions = [[1 / 3, "⅓"], [2 / 3, "⅔"], [0.5, "½"], [0.25, "¼"], [0.75, "¾"]];
    const fraction = fractions.find(([number]) => Math.abs(Number(value) - number) < 0.001);
    if (fraction) return fraction[1];
    return Number.isInteger(Number(value))
      ? String(value)
      : Number(value).toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  };

  const elements = {
    search: $("#searchInput"),
    grid: $("#recipeGrid"),
    resultCount: $("#resultCount"),
    difficulty: $("#difficultyFilter"),
    time: $("#timeFilter"),
    sort: $("#sortOrder"),
    loadMore: $("#loadMore"),
    empty: $("#emptyState"),
    dialog: $("#recipeDialog"),
    dialogContent: $("#dialogContent"),
  };

  function searchText(recipe) {
    return [
      recipe.title,
      recipe.cuisine,
      recipe.source.videoTitle,
      ...recipe.ingredients.map((item) => `${item.name} ${item.raw_text}`),
      ...recipe.steps.map((step) => step.text),
    ].join(" ").toLocaleLowerCase("ko");
  }

  recipes.forEach((recipe, index) => {
    recipe._order = index;
    recipe._search = searchText(recipe);
  });

  function filteredRecipes() {
    const query = state.query.trim().toLocaleLowerCase("ko");
    const filtered = recipes.filter((recipe) => {
      if (query && !recipe._search.includes(query)) return false;
      if (state.cuisine !== "전체" && recipe.cuisine !== state.cuisine) return false;
      if (state.difficulty !== "all" && recipe.difficulty !== Number(state.difficulty)) return false;
      if (state.time !== "all" && recipe.cookTime > Number(state.time)) return false;
      return true;
    });
    return filtered.sort((a, b) => {
      if (state.sort === "time") return a.cookTime - b.cookTime || a.title.localeCompare(b.title, "ko");
      if (state.sort === "ingredients") return a.ingredients.length - b.ingredients.length || a.title.localeCompare(b.title, "ko");
      if (state.sort === "title") return a.title.localeCompare(b.title, "ko");
      return a._order - b._order;
    });
  }

  function recipeCard(recipe) {
    const ingredients = recipe.ingredients.slice(0, 4).map((item) => item.name).join(" · ");
    const servings = recipe.servings ? `${recipe.servings}인분` : "인분 미확인";
    return `
      <article class="recipe-card" tabindex="0" role="button" data-id="${escapeHtml(recipe.id)}" aria-label="${escapeHtml(recipe.title)} 상세 보기">
        <div class="card-image">
          <img src="${escapeHtml(recipe.source.thumbnail)}" alt="" loading="lazy" referrerpolicy="no-referrer">
          <div class="card-badges">
            <span class="badge">${escapeHtml(recipe.cuisine)}</span>
            <span class="badge review">검수 필요</span>
          </div>
          <span class="card-time">약 ${escapeHtml(recipe.cookTime)}분</span>
        </div>
        <div class="card-copy">
          <h3>${escapeHtml(recipe.title)}</h3>
          <div class="card-meta">
            <span>난이도 ${difficultyNames[recipe.difficulty]}</span>
            <span>${servings}</span>
            <span>재료 ${recipe.ingredients.length}개</span>
          </div>
          <div class="ingredient-preview">${escapeHtml(ingredients)}</div>
        </div>
      </article>`;
  }

  function bindCardEvents() {
    $$(".recipe-card", elements.grid).forEach((card) => {
      const open = () => openRecipe(card.dataset.id);
      card.addEventListener("click", open);
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open();
        }
      });
      const image = $("img", card);
      image.addEventListener("error", () => {
        image.style.display = "none";
        image.parentElement.style.background = "linear-gradient(135deg,#d9aa60,#5f7f64)";
      }, { once: true });
    });
  }

  function render() {
    const filtered = filteredRecipes();
    const visible = filtered.slice(0, state.visible);
    elements.resultCount.textContent = filtered.length.toLocaleString("ko-KR");
    elements.grid.innerHTML = visible.map(recipeCard).join("");
    elements.empty.hidden = filtered.length !== 0;
    elements.grid.hidden = filtered.length === 0;
    elements.loadMore.hidden = filtered.length === 0 || visible.length >= filtered.length;
    bindCardEvents();
  }

  function openRecipe(id) {
    const recipe = recipes.find((item) => item.id === id);
    if (!recipe) return;
    const ingredientRows = recipe.ingredients.map((item, index) => {
      const amount = item.amount !== null && item.amount !== undefined
        ? `${formatAmount(item.amount)}${item.unit || ""}`
        : (item.unit || "");
      return `<li>
        <input id="ingredient-${index}" type="checkbox">
        <label for="ingredient-${index}">${escapeHtml(item.name)}${item.optional ? '<span class="optional">선택</span>' : ""}</label>
        <small>${escapeHtml(amount || item.raw_text)}</small>
      </li>`;
    }).join("");
    const stepRows = recipe.steps.map((step) => `<li><div>${escapeHtml(step.text)}${step.technique ? `<br><span class="technique">${escapeHtml(step.technique)}</span>` : ""}</div></li>`).join("");
    const tastes = Object.entries(recipe.taste).map(([key, value]) => `
      <div class="taste-row"><span>${tasteNames[key]}</span><div class="taste-track"><i style="width:${value * 20}%"></i></div><b>${value}</b></div>`).join("");
    const equipment = recipe.equipment.map((item) => `<li>${escapeHtml(item.name)}${item.required ? " · 필수" : ""}</li>`).join("");
    const servings = recipe.servings ? `${recipe.servings}인분` : "인분 미확인";
    elements.dialogContent.innerHTML = `
      <div class="dialog-hero">
        <img src="${escapeHtml(recipe.source.thumbnail)}" alt="" referrerpolicy="no-referrer">
        <div class="dialog-hero-copy">
          <span class="eyebrow">${escapeHtml(recipe.cuisine)} · ${escapeHtml(recipe.source.publishedAt || "게시일 미상")}</span>
          <h2 id="dialogTitle">${escapeHtml(recipe.title)}</h2>
          <div class="dialog-meta"><span>약 ${recipe.cookTime}분</span><span>·</span><span>${servings}</span><span>·</span><span>난이도 ${difficultyNames[recipe.difficulty]}</span><span>·</span><span>재료 ${recipe.ingredients.length}개</span></div>
        </div>
      </div>
      <div class="dialog-body">
        <div class="data-warning"><b>검수 전 레시피</b> · ${escapeHtml(recipe.note || "공개 영상 정보를 바탕으로 정리한 초안입니다.")}</div>
        <div class="recipe-columns">
          <section>
            <h3>재료</h3>
            <ul class="ingredient-list">${ingredientRows}</ul>
            <div class="taste-block"><h3>맛 프로필</h3><div class="taste-grid">${tastes}</div></div>
            <ul class="equipment-list">${equipment}</ul>
          </section>
          <section>
            <h3>조리 순서</h3>
            <ol class="step-list">${stepRows}</ol>
            <a class="source-button" href="${escapeHtml(recipe.source.videoUrl)}" target="_blank" rel="noreferrer">YouTube 원본 보기 ↗</a>
          </section>
        </div>
      </div>`;
    const dialogImage = $(".dialog-hero img", elements.dialogContent);
    dialogImage.addEventListener("error", () => { dialogImage.style.display = "none"; }, { once: true });
    elements.dialog.showModal();
    document.body.style.overflow = "hidden";
  }

  function resetFilters() {
    Object.assign(state, { query: "", cuisine: "전체", difficulty: "all", time: "all", sort: "recommended", visible: 18 });
    elements.search.value = "";
    elements.difficulty.value = "all";
    elements.time.value = "all";
    elements.sort.value = "recommended";
    $$("#cuisineTabs button").forEach((button) => button.classList.toggle("active", button.dataset.cuisine === "전체"));
    render();
  }

  function renderSummary() {
    const summary = data.summary;
    $("#totalRecipes").textContent = summary.recipeCount;
    $("#koreanRecipes").textContent = summary.cuisines.한식 || 0;
    $("#quickRecipes").textContent = recipes.filter((recipe) => recipe.cookTime <= 20).length;
    const ingredientNames = new Set(recipes.flatMap((recipe) => recipe.ingredients.map((item) => item.name)));
    $("#ingredientTypes").textContent = ingredientNames.size;

    const cuisineEntries = Object.entries(summary.cuisines);
    const total = cuisineEntries.reduce((sum, [, count]) => sum + count, 0);
    let cursor = 0;
    const stops = cuisineEntries.map(([name, count]) => {
      const start = cursor;
      cursor += count / total * 100;
      return `${cuisineColors[name]} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
    });
    $("#cuisineDonut").style.background = `conic-gradient(${stops.join(",")})`;
    $("#cuisineLegend").innerHTML = cuisineEntries.map(([name, count]) => `
      <div class="legend-row"><i class="legend-dot" style="background:${cuisineColors[name]}"></i><span>${escapeHtml(name)}</span><b>${count}</b></div>`).join("");
    $("#ingredientRank").innerHTML = summary.topIngredients.slice(0, 8).map((item, index) => `
      <div class="rank-row"><span class="rank-num">${String(index + 1).padStart(2, "0")}</span><b>${escapeHtml(item.name)}</b><span>${item.count}회</span></div>`).join("");
  }

  elements.search.addEventListener("input", (event) => { state.query = event.target.value; state.visible = 18; render(); });
  elements.difficulty.addEventListener("change", (event) => { state.difficulty = event.target.value; state.visible = 18; render(); });
  elements.time.addEventListener("change", (event) => { state.time = event.target.value; state.visible = 18; render(); });
  elements.sort.addEventListener("change", (event) => { state.sort = event.target.value; render(); });
  $("#cuisineTabs").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    state.cuisine = button.dataset.cuisine;
    state.visible = 18;
    $$("#cuisineTabs button").forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
  $$("[data-query]").forEach((button) => button.addEventListener("click", () => {
    elements.search.value = button.dataset.query;
    state.query = button.dataset.query;
    state.visible = 18;
    render();
    $("#catalog-title").scrollIntoView({ behavior: "smooth" });
  }));
  elements.loadMore.addEventListener("click", () => { state.visible += 18; render(); });
  $("#clearFilters").addEventListener("click", resetFilters);
  $("#emptyReset").addEventListener("click", resetFilters);
  $("#randomRecipe").addEventListener("click", () => {
    const pool = filteredRecipes();
    if (pool.length) openRecipe(pool[Math.floor(Math.random() * pool.length)].id);
  });
  $(".dialog-close").addEventListener("click", () => elements.dialog.close());
  elements.dialog.addEventListener("click", (event) => { if (event.target === elements.dialog) elements.dialog.close(); });
  elements.dialog.addEventListener("close", () => { document.body.style.overflow = ""; });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      elements.search.focus();
    }
  });

  renderSummary();
  render();
})();
