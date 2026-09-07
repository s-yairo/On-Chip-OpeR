import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

SCHEMA_VERSION = 1
PROCESS_KEYS = ("droplet_creation", "sorting_dispensing", "release")
PROCESS_STATUS_OPTIONS = ("未実施", "完了", "途中中止")
RESULT_STATUS_OPTIONS = (
    "良好",
    "条件付きで良好",
    "一部不良",
    "失敗",
    "途中中止",
    "未実施",
    "判定不能",
)


def empty_experiment_record_store() -> dict:
    return {"schema_version": SCHEMA_VERSION, "records": []}


def load_experiment_records(path: Path) -> dict:
    if not path.exists():
        return empty_experiment_record_store()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"実験記録データを読み込めませんでした: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("実験記録データの形式が正しくありません。")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("実験記録データの版が現在のソフトに対応していません。")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("実験記録データの records が正しくありません。")
    return payload


def save_experiment_records(path: Path, store: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temp_path.write_text(
            json.dumps(store, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(path)
    except OSError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError(f"実験記録データを保存できませんでした: {exc}") from exc


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_record_id(existing_ids: set[str]) -> str:
    prefix = datetime.now().strftime("EXP-%Y%m%d-%H%M%S")
    for _ in range(32):
        candidate = f"{prefix}-{uuid4().hex[:4].upper()}"
        if candidate not in existing_ids:
            return candidate
    raise ValueError("実験IDを作成できませんでした。もう一度お試しください。")


def create_experiment_record(store: dict) -> dict:
    """Create an unsaved draft record without mutating the store."""
    records = store.get("records", [])
    if not isinstance(records, list):
        raise ValueError("実験記録データの records が正しくありません。")

    existing_ids = {
        str(record.get("id", ""))
        for record in records
        if isinstance(record, dict) and record.get("id")
    }
    now = _timestamp()
    return {
        "id": _new_record_id(existing_ids),
        "created_at": now,
        "updated_at": now,
        "process_status": {
            "droplet_creation": "未実施",
            "sorting_dispensing": "未実施",
            "release": "未実施",
        },
        "result": "判定不能",
        "comment": "",
    }


def add_experiment_record(
    store: dict,
    draft: dict,
    *,
    process_status: dict[str, str],
    result: str,
    comment: str,
    condition_report: dict | None = None,
) -> dict:
    if any(process_status.get(key) not in PROCESS_STATUS_OPTIONS for key in PROCESS_KEYS):
        raise ValueError("主要工程の状態に使用できない値があります。")
    if result not in RESULT_STATUS_OPTIONS:
        raise ValueError("実験結果に使用できない値です。")

    records = store.setdefault("records", [])
    if not isinstance(records, list):
        raise ValueError("実験記録データの records が正しくありません。")

    record_id = str(draft.get("id", "")).strip()
    if not record_id:
        raise ValueError("実験IDが正しくありません。")
    if any(isinstance(item, dict) and item.get("id") == record_id for item in records):
        raise ValueError("同じ実験IDの記録が既に存在します。")

    record = {
        "id": record_id,
        "created_at": str(draft.get("created_at", "")) or _timestamp(),
        "updated_at": _timestamp(),
        "process_status": {key: process_status[key] for key in PROCESS_KEYS},
        "result": result,
        "comment": str(comment),
    }
    if condition_report is not None:
        record["condition_report"] = dict(condition_report)
    records.append(record)
    return record


def update_experiment_record(
    store: dict,
    record_id: str,
    *,
    process_status: dict[str, str],
    result: str,
    comment: str,
    condition_report: dict | None = None,
) -> dict:
    if any(process_status.get(key) not in PROCESS_STATUS_OPTIONS for key in PROCESS_KEYS):
        raise ValueError("主要工程の状態に使用できない値があります。")
    if result not in RESULT_STATUS_OPTIONS:
        raise ValueError("実験結果に使用できない値です。")

    records = store.get("records", [])
    for record in records:
        if isinstance(record, dict) and record.get("id") == record_id:
            record["process_status"] = {key: process_status[key] for key in PROCESS_KEYS}
            record["result"] = result
            record["comment"] = str(comment)
            if condition_report is not None:
                record["condition_report"] = dict(condition_report)
            record["updated_at"] = _timestamp()
            return record
    raise ValueError("指定された実験記録が見つかりません。")
