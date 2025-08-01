import os
from dotenv import load_dotenv
import logging
import asyncio

from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from supabase import create_client, Client

from src.scraper import scrape_alerts
from src.alerts import update_alerts
from src.bot_queries import start, send_lines, send_alerts, add_line, remove_line, handle_add_line_callback, handle_remove_line_callback
from src.bot_jobs import send_new_alerts


async def fetch_alerts(bot: Bot, supabase: Client, url: str) -> None:    
    while True:
        try:
            alerts_by_line = scrape_alerts(url)
            new_alerts_by_line = update_alerts(supabase, alerts_by_line)
            await send_new_alerts(bot, supabase, new_alerts_by_line)
        except Exception as e:
            logging.error(f"Error fetching alerts: {e}")
        await asyncio.sleep(60)


async def run_bot(app: ApplicationBuilder) -> None:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    async with app:
        fetch_task = asyncio.create_task(fetch_alerts(app.bot,
                                                      app.bot_data["supabase"],
                                                      app.bot_data["trenes_arg_url"]))
        try:
            await app.start()
            await app.updater.start_polling()
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            fetch_task.cancel()
            try:
                await fetch_task
            except asyncio.CancelledError:
                pass
            await app.updater.stop()
            await app.stop()


async def main() -> None:
    load_dotenv()
    trenes_arg_url = "https://www.argentina.gob.ar/transporte/trenes-argentinos/Modificaciones-en-el-servicio-y-novedades"

    token: str = os.environ.get("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lines", send_lines))
    app.add_handler(CommandHandler("alerts", send_alerts))
    app.add_handler(CommandHandler("add", add_line))
    app.add_handler(CommandHandler("remove", remove_line))
    
    app.add_handler(CallbackQueryHandler(handle_add_line_callback, pattern="^add_line:"))
    app.add_handler(CallbackQueryHandler(handle_remove_line_callback, pattern="^remove_line:"))

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    app.bot_data["trenes_arg_url"] = trenes_arg_url
    app.bot_data["supabase"] = supabase
    app.bot_data["bot"] = app.bot
    await run_bot(app)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
