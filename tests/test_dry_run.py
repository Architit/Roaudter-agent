from roaudter_agent import dry_run

def test_dry_run_ok():
    assert dry_run() == "ok"
