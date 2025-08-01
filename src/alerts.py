import json
import hashlib
from collections import defaultdict
from supabase import Client


def get_lines_map(supabase: Client) -> dict[str, int]:
    return {
        line["name"]: line["id"]
        for line in supabase.table("lines")
                            .select("id", "name")
                            .execute().data
    }


def get_prev_alerts_keys(supabase: Client) -> set[tuple[int, str]]:
    return {
        (alert["line_id"], alert["alert_hash"])
        for alert in supabase.table("alerts")
                             .select("line_id", "alert_hash")
                             .execute().data
    }


def get_new_alerts(lines_map: dict[str, int],
                   alerts_by_line: defaultdict[str, list[dict]]) -> list[dict]:
    new_alerts = {}
    for line, alerts in alerts_by_line.items():
        line_id = lines_map.get(line)
        if not line_id:
            continue
        for alert in alerts:
            alert_hash = hashlib.sha256(json.dumps(alert, sort_keys=True).encode()).hexdigest()
            new_alerts[(line_id, alert_hash)] = alert
    return new_alerts


def update_alerts(supabase: Client, alerts_by_line: defaultdict[str, list[dict]]) -> defaultdict[str, list[dict]]:
    prev_alerts_keys = get_prev_alerts_keys(supabase)

    new_alerts = get_new_alerts(get_lines_map(supabase), alerts_by_line)
    new_alerts_keys = set(new_alerts.keys())

    alerts_keys_to_insert = new_alerts_keys - prev_alerts_keys
    alerts_to_insert = [
        {
            "line_id": line_id,
            "alert_hash": alert_hash,
            "type": new_alerts[(line_id, alert_hash)]["type"],
            "title": new_alerts[(line_id, alert_hash)]["title"],
            "description": new_alerts[(line_id, alert_hash)]["description"]
        }
        for (line_id, alert_hash) in alerts_keys_to_insert
    ]
    if alerts_keys_to_insert:
        supabase.table("alerts").insert(alerts_to_insert).execute()

    alerts_keys_to_delete = prev_alerts_keys - new_alerts_keys
    if alerts_keys_to_delete:
        supabase.table("alerts").delete().or_(*[
            f"and(line_id.eq.{line_id}, alert_hash.eq.{alert_hash})"
            for (line_id, alert_hash) in alerts_keys_to_delete
        ]).execute()

    new_alerts_by_line = defaultdict(list)
    for (line_id, alert_hash), alert in new_alerts.items():
        if (line_id, alert_hash) in alerts_keys_to_insert:
            new_alerts_by_line[line_id].append(alert)
    return new_alerts_by_line
