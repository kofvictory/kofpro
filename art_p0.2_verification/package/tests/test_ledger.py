from art_p0.ledger import RunLedger, RunRecord


def test_append_only_round_trip(tmp_path):
    ledger = RunLedger(tmp_path / "runs.jsonl")
    r = RunRecord.new(
        task_id="t1",
        harness_id="h0",
        harness_hash="abc",
        resource_interface_id="B4",
        seed=7,
        tool_budget_limit=4,
    )
    r.tool_calls_used = 3
    r.success_official = True
    ledger.append(r)

    rows = ledger.read_all()
    assert len(rows) == 1
    assert rows[0].run_id == r.run_id
    assert rows[0].tool_calls_used == 3
    assert rows[0].finished_at is not None
