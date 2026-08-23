from art_p0.hashing import canonical_json, harness_hash


def test_hash_is_order_invariant_for_mapping_keys():
    a = {"prompt": "x", "policy": {"b": 2, "a": 1}}
    b = {"policy": {"a": 1, "b": 2}, "prompt": "x"}
    assert canonical_json(a) == canonical_json(b)
    assert harness_hash(a) == harness_hash(b)


def test_hash_changes_when_harness_changes():
    assert harness_hash({"prompt": "x"}) != harness_hash({"prompt": "y"})
