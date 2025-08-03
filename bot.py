import os
from dotenv import load_dotenv
import asyncio
import logging

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from supabase import acreate_client, AsyncClient

from src.scraper import scrape_alerts
from src.alerts import update_alerts
from src.bot import (
    start, send_lines, send_alerts, add_line, remove_line,
    handle_add_line_callback, handle_remove_line_callback,
    broadcast_alerts
)


async def sync_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    alerts_by_line = await scrape_alerts(context.bot_data["trenes_arg_url"])
    alerts_to_broadcast = await update_alerts(context.bot_data["supabase"], alerts_by_line)
    await broadcast_alerts(context, alerts_to_broadcast)


def main() -> None:
    load_dotenv()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: AsyncClient = asyncio.run(acreate_client(url, key))

    asyncio.set_event_loop(asyncio.new_event_loop())

    token: str = os.environ.get("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lines", send_lines))
    app.add_handler(CommandHandler("alerts", send_alerts))
    app.add_handler(CommandHandler("add", add_line))
    app.add_handler(CommandHandler("remove", remove_line))
    app.add_handler(CallbackQueryHandler(handle_add_line_callback, pattern="^add_line:"))
    app.add_handler(CallbackQueryHandler(handle_remove_line_callback, pattern="^remove_line:"))
    app.bot_data["trenes_arg_url"] = (
        "https://www.argentina.gob.ar/transporte/trenes-argentinos/"
        "Modificaciones-en-el-servicio-y-novedades"
    )
    app.bot_data["supabase"] = supabase
    app.job_queue.run_repeating(sync_alerts, interval=300, first=0)
    app.run_polling(stop_signals=())


if __name__ == "__main__":
    main()
