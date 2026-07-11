"""Desktop handoff queue — trusted local registrations reach the desktop.

save_card is the single funnel every runtime copy uses, so the enqueue rule
here is what guarantees "build anywhere → shows up in the Agentlas Desktop
library". The qualification gate is deliberately strict: routing_ready forge
experiments (100+ cards live in real homes) must never flood the desktop.
"""

import json

from agentlas_cloud.networking.card_store import save_card
from agentlas_cloud.networking.desktop_sync import (
    DONE_DIR,
    PENDING_DIR,
    enqueue_desktop_sync,
    qualifies_for_desktop,
)


def _package(tmp_path, name="pkg"):
    pkg = tmp_path / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "agentlas.json").write_text('{"slug": "demo"}', encoding="utf-8")
    return pkg


def _card(pkg, **overrides):
    card = {
        "id": "local/demo-agent",
        "type": "agent",
        "name": "Demo Agent",
        "routing_status": "trusted",
        "source": {"kind": "local_path", "ref": str(pkg)},
    }
    card.update(overrides)
    return card


def test_trusted_local_card_enqueues_pending_entry(tmp_path):
    home = tmp_path / "networking"
    pkg = _package(tmp_path)
    save_card(home, _card(pkg))

    pending = home / PENDING_DIR / "local-demo-agent.json"
    assert pending.is_file()
    entry = json.loads(pending.read_text(encoding="utf-8"))
    assert entry["id"] == "local/demo-agent"
    assert entry["ref"] == str(pkg)
    assert entry["content_hash"]


def test_non_trusted_and_non_local_cards_never_enqueue(tmp_path):
    home = tmp_path / "networking"
    pkg = _package(tmp_path)
    # routing_ready 포지(실험) 카드 — 데스크탑에 홍수 나면 안 된다.
    save_card(home, _card(pkg, id="free/researcher-001", routing_status="routing_ready"))
    save_card(home, _card(pkg, id="paid/team-x", type="team", routing_status="routing_ready"))
    save_card(home, _card(pkg, routing_status="candidate"))
    save_card(home, _card(pkg, stale=True))
    assert not (home / PENDING_DIR).exists()


def test_relative_or_missing_ref_disqualifies(tmp_path):
    pkg = _package(tmp_path)
    assert qualifies_for_desktop(_card(pkg))
    assert not qualifies_for_desktop(_card(pkg, source={"kind": "local_path", "ref": "."}))
    assert not qualifies_for_desktop(_card(pkg, source={"kind": "local_path", "ref": str(pkg / "gone")}))
    assert not qualifies_for_desktop(_card(pkg, source={"kind": "hub"}))
    # 패키지 마커가 없는 빈 폴더는 임포트 대상이 아니다.
    empty = pkg.parent / "empty"
    empty.mkdir()
    assert not qualifies_for_desktop(_card(pkg, source={"kind": "local_path", "ref": str(empty)}))


def test_done_hash_prevents_reenqueue_until_card_changes(tmp_path):
    home = tmp_path / "networking"
    pkg = _package(tmp_path)
    card = _card(pkg)
    saved_to = save_card(home, card)
    saved = json.loads(saved_to.read_text(encoding="utf-8"))

    pending = home / PENDING_DIR / "local-demo-agent.json"
    entry = json.loads(pending.read_text(encoding="utf-8"))
    # 데스크탑이 드레인 완료: pending → done (content_hash 보존).
    done = home / DONE_DIR / "local-demo-agent.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    done.write_text(json.dumps(entry), encoding="utf-8")
    pending.unlink()

    # 같은 내용 재저장(reindex churn) — 다시 큐잉하지 않는다.
    assert enqueue_desktop_sync(home, saved) is None
    assert not pending.exists()

    # 카드 내용이 바뀌면 다시 큐잉된다.
    changed = dict(saved)
    changed.pop("integrity", None)
    changed["name"] = "Demo Agent v2"
    save_card(home, changed)
    assert pending.is_file()
