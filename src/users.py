import logging
import asyncio
from supabase import AsyncClient



async def register_user(supabase: AsyncClient,
                  user_id: int,
                  chat_id: int,
                  username: str,
                  first_name: str,
                  last_name: str) -> None:
    try:
        await (
            supabase.table("users")
                    .insert({
                        "id": user_id,
                        "chat_id": chat_id,
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name
                    })
                    .execute()
        )
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e):
            logging.warning(f"User {user_id} already exists.")
        else:
            raise e
        

async def get_chat_ids(supabase: AsyncClient, line_id: int) -> list[int]:
    response = await (
        supabase.table("subscriptions")
                .select("users(chat_id)")
                .eq("line_id", line_id)
                .execute()
    )
    return [
        entry["users"]["chat_id"]
        for entry in response.data
    ]


async def get_available_lines(supabase: AsyncClient, user_id: int) -> list[dict]:
    all_lines_task = supabase.table("lines").select("id, name").execute()
    user_subs_task = (
        supabase.table("subscriptions")
                .select("line_id")
                .eq("user_id", user_id)
                .execute()
    )
    all_lines_resp, user_subs_resp = await asyncio.gather(all_lines_task, user_subs_task)
    subscribed_line_ids = {sub["line_id"] for sub in user_subs_resp.data}
    return [
        {"id": line["id"], "name": line["name"]}
        for line in all_lines_resp.data
        if line["id"] not in subscribed_line_ids
    ]




async def get_user_lines(supabase: AsyncClient, user_id: int) -> list[dict]:
    response = await (
        supabase.table("subscriptions")
                .select("lines(id, name)")
                .eq("user_id", user_id)
                .execute()
    )
    return [
        {"id": entry["lines"]["id"], "name": entry["lines"]["name"]}
        for entry in response.data
    ]


async def get_user_alerts(supabase: AsyncClient, user_id: int) -> dict[str, list[dict]]:
    response = await (
        supabase.table("subscriptions")
                .select("lines(name, alerts(type, title, description))")
                .eq("user_id", user_id)
                .execute()
    )
    alerts_by_line = {}
    for entry in response.data:
        line = entry.get("lines")
        if not line or "name" not in line:
            continue
        line_name = line["name"]
        alerts = line.get("alerts", [])
        alerts_by_line[line_name] = alerts
    return alerts_by_line


async def add_user_line(supabase: AsyncClient, user_id: int, line_id: int) -> None:
    try:
        await (
            supabase.table("subscriptions")
                    .insert({
                        "user_id": user_id,
                        "line_id": line_id
                    })
                    .execute()
        )
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e):
            logging.warning(f"User {user_id} already subscribed to line {line_id}.")
        else:
            raise e
        

async def remove_user_line(supabase: AsyncClient, user_id: int, line_id: int) -> None:
    try:
        await (
            supabase.table("subscriptions")
                    .delete()
                    .match({
                        "user_id": user_id,
                        "line_id": line_id
                    })
                    .execute()
        )
    except Exception as e:
        logging.error(f"Error removing user {user_id} from line {line_id}: {e}")
        raise e
