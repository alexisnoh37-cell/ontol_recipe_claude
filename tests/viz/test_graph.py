"""GET /graph (docs/plan.md 부록 D-1~D-3): 컴파일 결과·레시피 시드를 빠짐없이 노드·간선으로 옮기는지."""

from __future__ import annotations

from collections import Counter

from api.viz import alg_link, der_link, isa_link


def get_graph(client, **params):
    r = client.get("/graph", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_node_counts_match_knowledge_and_published_recipes(client, data):
    g = get_graph(client)
    kinds = Counter(n["kind"] for n in g["nodes"])
    ck = data.knowledge
    published = [r for r in data.recipes if r.status == "published"]
    assert kinds == {"ingredient": len(ck.ingredients), "allergen_group": len(ck.allergen_groups),
                     "recipe": len(published)}
    assert g["stats"]["nodes"] == len(g["nodes"]) and g["stats"]["links"] == len(g["links"])
    assert g["knowledge_hash"] == ck.source_hash


def test_ids_unique_and_links_point_to_nodes(client):
    g = get_graph(client, recipes="all")
    ids = [n["id"] for n in g["nodes"]]
    assert len(ids) == len(set(ids))
    link_ids = [lk["id"] for lk in g["links"]]
    assert len(link_ids) == len(set(link_ids))
    node_ids = set(ids)
    assert all(lk["source"] in node_ids and lk["target"] in node_ids for lk in g["links"])


def test_layers_follow_structure(client, data):
    g = get_graph(client)
    has_source = {r.from_id for r in data.knowledge.relations if r.type == "derived_from"}
    for n in g["nodes"]:
        if n["kind"] == "allergen_group":
            assert n["layer"] == 1
        elif n["kind"] == "recipe":
            assert n["layer"] == 4
        else:
            iid = n["id"].removeprefix("ing:")
            assert n["layer"] == (3 if iid in has_source else 2), n["id"]
            if n["is_concept"]:
                assert n["layer"] == 2
    # derived_from이 있지만 가공품이 아닌 재료(콩나물)는 3층에 있고 is_processed false로 표시된다(viz-0 결정)
    sprouts = next(n for n in g["nodes"] if n["id"] == "ing:soybean_sprouts")
    assert sprouts["layer"] == 3 and sprouts["is_processed"] is False


def test_link_counts_match_compiled_rows(client, data):
    g = get_graph(client)
    ck = data.knowledge
    types = Counter(lk["type"] for lk in g["links"])
    published = [r for r in data.recipes if r.status == "published"]
    assert types["is_a"] == sum(r.type == "is_a" for r in ck.relations)
    assert types["derived_from"] == sum(r.type == "derived_from" for r in ck.relations)
    assert types["allergen"] == len(ck.ingredient_allergens)
    assert types["bundle_member"] == len(ck.group_members)
    assert types["uses"] == sum(1 for r in published for line in r.ingredients if line.ingredient)
    assert "substitute" not in types


def test_uses_links_keep_role_optional_and_line_no(client, data):
    g = get_graph(client)
    spec = next(r for r in data.recipes if r.id == "gyeranjjim")
    uses = {lk["line_no"]: lk for lk in g["links"] if lk["type"] == "uses" and lk["source"] == "rcp:gyeranjjim"}
    for n, line in enumerate(spec.ingredients, start=1):
        assert uses[n]["target"] == f"ing:{line.ingredient}"
        assert uses[n]["role"] == line.role and uses[n]["optional"] == line.optional


def test_every_closure_path_is_walkable_on_graph_links(client, data):
    """화면은 via를 path_links로만 그린다. 모든 closure 경로의 연속 쌍이 그래프 간선으로 이어져야 한다."""
    g = get_graph(client, recipes="none")
    links = {lk["id"] for lk in g["links"]}
    groups = {x.id: x for x in data.knowledge.allergen_groups}
    checked = 0
    for row in data.knowledge.allergen_closure:
        if groups[row.allergen_group_id].kind != "base":
            continue
        via = row.via
        assert via[0] == row.ingredient_id
        for a, b in zip(via, via[1:]):
            assert {isa_link(a, b), isa_link(b, a), der_link(a, b)} & links, (row, a, b)
        assert alg_link(via[-1], row.allergen_group_id) in links, row
        checked += 1
    assert checked > 100


def test_bundle_nodes_list_members(client, data):
    g = get_graph(client, recipes="none")
    bundles = [n for n in g["nodes"] if n["kind"] == "allergen_group" and n["group_kind"] == "bundle"]
    assert bundles and all(n["category"] == "bundle" and n["members"] for n in bundles)
    cats = Counter(n["category"] for n in g["nodes"] if n["kind"] == "allergen_group")
    assert cats["official"] == 19


def test_recipe_scope_and_limit(client, data):
    assert not [n for n in get_graph(client, recipes="none")["nodes"] if n["kind"] == "recipe"]
    g = get_graph(client, max_recipes=5)
    assert sum(n["kind"] == "recipe" for n in g["nodes"]) == 5
    assert all(lk["source"] in {n["id"] for n in g["nodes"]} for lk in g["links"])
    assert sum(n["kind"] == "recipe" for n in get_graph(client, recipes="all")["nodes"]) == len(data.recipes)


def test_etag_returns_304_when_unchanged(client):
    r = client.get("/graph")
    etag = r.headers["etag"]
    r2 = client.get("/graph", headers={"If-None-Match": etag})
    assert r2.status_code == 304 and r2.headers["etag"] == etag
    assert client.get("/graph", params={"recipes": "none"}).headers["etag"] != etag


def test_ingredient_allergy_paths_walk_from_ingredient_to_group(client, data):
    """재료 선택 시 강조할 알레르기 경로(viz-3 보완): via 순서대로 이어지고 마지막이 그룹 지정 링크다."""
    g = get_graph(client)
    links = {lk["id"]: lk for lk in g["links"]}
    base = {gr.id for gr in data.knowledge.allergen_groups if gr.kind == "base"}
    rows = {(c.ingredient_id, c.allergen_group_id): c for c in data.knowledge.allergen_closure
            if c.allergen_group_id in base}
    seen = 0
    for n in g["nodes"]:
        if n["kind"] != "ingredient":
            continue
        assert len(n["allergens"]) == sum(1 for i, _ in rows if i == n["id"][4:])
        for a in n["allergens"]:
            row = rows[(n["id"][4:], a["group"][3:])]
            assert a["via"] == [f"ing:{x}" for x in row.via] and a["certainty"] == row.certainty
            path = [links[x] for x in a["path_links"]]
            assert len(path) == len(row.via)  # via 쌍 수 + 그룹 지정 1
            assert path[-1]["type"] == "allergen" and path[-1]["target"] == a["group"]
            assert path[-1]["source"] == a["via"][-1]
            walked = [a["via"][0]]
            for lk in path[:-1]:
                walked.append(lk["target"] if lk["source"] == walked[-1] else lk["source"])
            assert walked == a["via"]
            seen += 1
    assert seen == len(rows)
    nodes = {n["id"]: n for n in g["nodes"]}
    kimchi_shrimp = next(a for a in nodes["ing:kimchi"]["allergens"] if a["group"] == "ag:shrimp")
    assert "ing:saeujeot" in kimchi_shrimp["via"] and kimchi_shrimp["certainty"] == "possible"
    assert kimchi_shrimp["via"][0] == "ing:kimchi" and kimchi_shrimp["path_links"][-1].endswith(">shrimp")


def test_recipe_allergens_join_lines_with_compiled_closure(client, data):
    """레시피 정보 패널의 "걸리는 알레르기": 줄마다 기본 그룹 closure를 모은 것과 같다(선택 재료·possible 표시 포함)."""
    g = get_graph(client)
    base = {gr.id for gr in data.knowledge.allergen_groups if gr.kind == "base"}
    closure: dict[str, list] = {}
    for c in data.knowledge.allergen_closure:
        if c.allergen_group_id in base:
            closure.setdefault(c.ingredient_id, []).append(c)
    specs = {r.id: r for r in data.recipes}
    for n in (n for n in g["nodes"] if n["kind"] == "recipe"):
        expected: dict[str, list[tuple]] = {}
        for k, line in enumerate(specs[n["id"][4:]].ingredients, start=1):
            for c in closure.get(line.ingredient or "", []):
                expected.setdefault(f"ag:{c.allergen_group_id}", []).append(
                    (f"ing:{line.ingredient}", c.certainty, line.optional, k))
        got = {a["group"]: a for a in n["allergens"]}
        assert set(got) == set(expected), n["id"]
        for gid, hits in expected.items():
            a = got[gid]
            assert sorted((h["ingredient"], h["certainty"], h["optional"], h["line_no"]) for h in a["hits"]) == sorted(hits)
            assert a["certainty"] == ("definite" if any(h[1] == "definite" for h in hits) else "possible")
            assert a["optional_only"] == all(h[2] for h in hits)
    steam = next(n for n in g["nodes"] if n["id"] == "rcp:gyeranjjim")
    shrimp = next(a for a in steam["allergens"] if a["group"] == "ag:shrimp")
    assert shrimp["optional_only"] and shrimp["hits"][0]["ingredient"] == "ing:saeujeot"
    assert any(a["group"] == "ag:egg" and not a["optional_only"] for a in steam["allergens"])


def test_recipe_selection_paths_match_info_panel(client):
    """레시피 선택 시 그래프가 그리는 그룹(재료 줄의 재료 노드 allergens 경로) = 정보 패널 "걸리는 알레르기".

    화면(scene.js selectionFocus)과 같은 규칙: uses 링크마다 재료 노드 allergens를 따라가고,
    possible이거나 선택 재료면 흐린 경로. 그룹이 진하게 그려지는 조건 = definite이면서 선택 재료가 아닌 줄이 있음.
    """
    g = get_graph(client, recipes="all")
    nodes = {n["id"]: n for n in g["nodes"]}
    links = {lk["id"] for lk in g["links"]}
    for r in (n for n in g["nodes"] if n["kind"] == "recipe"):
        drawn: dict[str, bool] = {}
        for lk in (lk for lk in g["links"] if lk["type"] == "uses" and lk["source"] == r["id"]):
            for a in nodes[lk["target"]]["allergens"]:
                assert all(x in links for x in a["path_links"])
                strong = a["certainty"] == "definite" and not lk["optional"]
                drawn[a["group"]] = drawn.get(a["group"], False) or strong
        panel = {a["group"]: any(h["certainty"] == "definite" and not h["optional"] for h in a["hits"])
                 for a in r["allergens"]}
        assert drawn == panel, r["id"]
    tonkatsu = {nodes[a["group"]]["name"]: a["certainty"] for a in nodes["rcp:tonkatsu"]["allergens"]}
    assert tonkatsu["알류(가금류)"] == "definite" and tonkatsu["밀"] == "definite"
    assert all(tonkatsu[x] == "possible" for x in ("대두", "토마토", "아황산류"))
