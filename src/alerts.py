import json
import hashlib
from collections import defaultdict
from supabase import AsyncClient


async def get_lines_map(supabase: AsyncClient) -> dict[str, str]:
    response = await (
        supabase.table("lines")
                .select("id, name")
                .execute()
    )
    return {
        line["id"]: line["name"]
        for line in response.data
    }


async def get_prev_alerts_keys(supabase: AsyncClient) -> set[tuple[str, str]]:
    response = await (
        supabase.table("alerts")
                .select("line_id, alert_hash")
                .execute()
    )
    return {
        (alert["line_id"], alert["alert_hash"])
        for alert in response.data
    }


def get_new_alerts(lines_map: dict[str, str],
                   alerts_by_line: defaultdict[str, list[dict]]) -> dict[tuple[str, str], dict]:
    lines_map = {line_name: line_id for line_id, line_name in lines_map.items()}
    new_alerts = {}
    for line, alerts in alerts_by_line.items():
        line_id = lines_map.get(line)
        if not line_id:
            continue
        for alert in alerts:
            alert_hash = hashlib.sha256(json.dumps(alert, sort_keys=True).encode()).hexdigest()
            new_alerts[(line_id, alert_hash)] = alert
    return new_alerts


def get_alerts_to_broadcast(lines_map: dict[str, str],
                            alerts: dict[tuple[str, str], dict],
                            alerts_keys_to_broadcast: list[tuple[str, str]]) -> defaultdict[str, dict]:
    new_alerts_by_line = defaultdict(lambda: {"line_name": "", "alerts": []})
    for line_id, alert_hash in alerts_keys_to_broadcast:
        new_alerts_by_line[line_id]["line_name"] = lines_map.get(line_id, "")
        new_alerts_by_line[line_id]["alerts"].append({
            "type": alerts[(line_id, alert_hash)]["type"],
            "title": alerts[(line_id, alert_hash)]["title"],
            "description": alerts[(line_id, alert_hash)]["description"],
        })
    return new_alerts_by_line


async def update_alerts(supabase: AsyncClient,
                        alerts_by_line: defaultdict[str, list[dict]]) -> defaultdict[str, list[dict]]:
    prev_alerts_keys = await get_prev_alerts_keys(supabase)

    lines_map = await get_lines_map(supabase)
    new_alerts = get_new_alerts(lines_map, alerts_by_line)
    new_alerts_keys = set(new_alerts.keys())

    alerts_keys_to_insert = new_alerts_keys - prev_alerts_keys
    alerts_to_insert = [
        {
            "line_id": line_id,
            "alert_hash": alert_hash,
            "type": new_alerts[(line_id, alert_hash)]["type"],
            "title": new_alerts[(line_id, alert_hash)]["title"],
            "description": new_alerts[(line_id, alert_hash)]["description"],
        }
        for (line_id, alert_hash) in alerts_keys_to_insert
    ]
    if alerts_keys_to_insert:
        await (
            supabase.table("alerts")
                    .insert(alerts_to_insert)
                    .execute()
        )

    alerts_keys_to_delete = prev_alerts_keys - new_alerts_keys
    if alerts_keys_to_delete:
        await (
            supabase.table("alerts")
                    .delete()
                    .or_(",".join(f"and(line_id.eq.{line_id},alert_hash.eq.{alert_hash})"
                                  for line_id, alert_hash in alerts_keys_to_delete))
                    .execute()
        )

    return get_alerts_to_broadcast(lines_map, new_alerts, alerts_keys_to_insert)
