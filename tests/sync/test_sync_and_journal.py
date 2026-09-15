"""Unit tests for stable IDs, ChangeJournal delta tracking, and tombstones."""

from pathlib import Path
from novel_agent.sync.ids import generate_stable_id
from novel_agent.sync.journal import ChangeJournal, OperationType
from novel_agent.sync.providers import NoopSyncProvider


def test_stable_id_generation():
    id1 = generate_stable_id("chap")
    id2 = generate_stable_id("chap")
    assert id1.startswith("chap_")
    assert id2.startswith("chap_")
    assert id1 != id2


def test_change_journal_lifecycle(tmp_path: Path):
    db_file = tmp_path / "journal.db"
    journal = ChangeJournal(db_file)

    assert journal.get_latest_seq() == 0

    # Record chapter insertion
    e1 = journal.record_change(
        entity_type="chapter",
        entity_id="chap_001",
        operation=OperationType.INSERT,
        revision=1,
        device_id="device_alpha",
        payload={"title": "第1章", "content": "正文开头"},
    )
    assert e1.seq == 1
    assert journal.get_latest_seq() == 1

    # Record character update
    e2 = journal.record_change(
        entity_type="character",
        entity_id="char_001",
        operation=OperationType.UPDATE,
        revision=2,
        device_id="device_alpha",
        payload={"name": "林野", "role": "主角"},
    )
    assert e2.seq == 2

    # Record chapter tombstone delete
    e3 = journal.record_tombstone(
        entity_type="chapter",
        entity_id="chap_002",
        revision=3,
        device_id="device_alpha",
    )
    assert e3.seq == 3
    assert e3.operation == OperationType.DELETE

    # Delta query: get changes after seq 1
    deltas = journal.get_changes_after(last_seq=1)
    assert len(deltas) == 2
    assert deltas[0].entity_id == "char_001"
    assert deltas[1].operation == OperationType.DELETE

    # Delta query: get changes after latest seq
    empty_deltas = journal.get_changes_after(last_seq=3)
    assert len(empty_deltas) == 0


def test_noop_sync_provider():
    provider = NoopSyncProvider()
    ok, msg = provider.push_deltas([])
    assert ok is True
    assert "本地" in msg
    pulled, seq = provider.pull_deltas(10)
    assert pulled == []
    assert seq == 10
