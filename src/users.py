import logging
from supabase import Client


def register_user(supabase: Client,
                  user_id: int,
                  chat_id: int,
                  username: str,
                  first_name: str,
                  last_name: str) -> None:
    try:
        supabase.table("users").insert({
            "id": user_id,
            "chat_id": chat_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }).execute()
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e):
            logging.warning(f"User {user_id} already exists.")
        else:
            raise e
        

def get_lines(supabase: Client) -> list[dict]:
    response = supabase.table("lines").select("id", "name").execute()
    return [{"id": line["id"], "name": line["name"]} for line in response.data]


def get_lines_to_add(supabase: Client, user_id: int) -> list[dict]:
    lines = get_lines(supabase)
    user_lines = get_user_lines(supabase, user_id)
    return [line for line in lines if line not in user_lines]


def get_user_lines(supabase: Client, user_id: int) -> list[dict]:
    response = (
        supabase.table("subscriptions")
                .select("lines(id, name)")
                .eq("user_id", user_id)
                .execute()
    )
    return [{"id": entry["lines"]["id"], "name": entry["lines"]["name"]} for entry in response.data if entry.get("lines")]


def get_user_alerts(supabase: Client, user_id: int) -> dict[str, list[dict]]:
    response = (
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


def add_user_line(supabase: Client, user_id: int, line_id: int) -> None:
    try:
        supabase.table("subscriptions").insert({
            "user_id": user_id,
            "line_id": line_id
        }).execute()
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e):
            logging.warning(f"User {user_id} already subscribed to line {line_id}.")
        else:
            raise e
        

def remove_user_line(supabase: Client, user_id: int, line_id: int) -> None:
    try:
        supabase.table("subscriptions").delete().match({
            "user_id": user_id,
            "line_id": line_id
        }).execute()
    except Exception as e:
        logging.error(f"Error removing user {user_id} from line {line_id}: {e}")
        raise e
