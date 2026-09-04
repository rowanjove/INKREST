import threading
from pathlib import Path
from novel_agent.state.sqlite_schema import safe_connection, safe_write_connection


def test_concurrent_safe_write_connections(tmp_path: Path):
    db_path = tmp_path / 'concurrent_test.sqlite'
    with safe_write_connection(db_path) as conn:
        conn.execute('CREATE TABLE concurrent_records (id INT PRIMARY KEY, val TEXT)')
        conn.commit()

    errors = []

    def writer_task(worker_id: int):
        try:
            for i in range(15):
                with safe_write_connection(db_path) as conn:
                    conn.execute(
                        'INSERT OR REPLACE INTO concurrent_records VALUES (?, ?)',
                        (worker_id * 1000 + i, f'payload-{worker_id}-{i}')
                    )
                    conn.commit()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer_task, args=(w,)) for w in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f'Concurrent write errors: {errors}'

    with safe_connection(db_path) as conn:
        total = conn.execute('SELECT count(*) FROM concurrent_records').fetchone()[0]
    assert total == 8 * 15


def test_safe_write_connection_releases_lock_on_error(tmp_path: Path):
    db_path = tmp_path / "lock_error_test.sqlite"
    lock = safe_connection.get_lock(db_path)

    try:
        with safe_write_connection(db_path):
            raise RuntimeError("Intentional write failure")
    except RuntimeError:
        pass

    # Verify the lock is free and can be acquired immediately
    acquired = lock.acquire(blocking=False)
    assert acquired is True
    lock.release()
