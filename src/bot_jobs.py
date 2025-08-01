from collections import defaultdict

from telegram import Bot
from supabase import Client


def get_lines_map(supabase: Client) -> dict[str, int]:
    return {
        line["id"]: line["name"]
        for line in supabase.table("lines")
                            .select("id", "name")
                            .execute().data
    }


def get_chat_ids(supabase: Client, line_id: int) -> list[int]:
    response = (supabase.table("subscriptions")
                .select("users(chat_id)")
                .eq("line_id", line_id)
                .execute())
    return [entry["users"]["chat_id"] for entry in response.data]


async def send_new_alerts(bot: Bot, supabase: Client, alerts_by_line: defaultdict[str, list[dict]]) -> None:
    lines_map = get_lines_map(supabase)
    for line_id, alerts in alerts_by_line.items():
        if not alerts:
            continue
        line_name = lines_map.get(line_id)
        if not line_name:
            continue

        msg = f"🚆<b>{line_name}</b>\n"
        for alert in alerts:
            msg += f"\n🛤️<b>{alert['title']}</b>\n" if alert["title"] else "\n"
            msg += f"{alert['type'].capitalize()}: {alert['description']}\n" if alert["description"] else ""

        chat_ids = get_chat_ids(supabase, line_id)
        for chat_id in chat_ids:
            await bot.send_message(chat_id, msg, parse_mode="HTML")
