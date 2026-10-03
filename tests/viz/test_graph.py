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
