from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from src.users import register_user, get_user_lines, get_available_lines, get_user_alerts, add_user_line, remove_user_line


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    register_user(context.bot_data["supabase"],
                  update.effective_user.id,
                  update.effective_chat.id,
                  update.effective_user.username,
                  update.effective_user.first_name,
                  update.effective_user.last_name)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"<b>¡Hola {update.effective_user.first_name}! "
        "Soy <a href='https://github.com/segusantos/trenes-arg-bot'>TrenesArgBot</a>, "
        "tu asistente para alertas de trenes en Argentina.</b> 🚆🇦🇷\n\n"
        "Usá /lines para listar las líneas que tenés seleccionadas y /alerts para ver tus alertas actuales. "
        "Podés agregar y eliminar líneas con /add y /remove.\n\n"
        "<b>Cada vez que haya una novedad, te enviaré un mensaje. "
        "¡Buen viaje! 🛤️😊</b>",
        parse_mode="HTML"
    )


async def send_lines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_lines = get_user_lines(context.bot_data["supabase"],
                                update.effective_user.id)
    msg = ("Tus líneas de trenes seleccionadas son:\n" +
           "\n".join([f"🚆 <b>{line['name']}</b>" for line in user_lines])
            if user_lines else "No tenés líneas seleccionadas.")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg,
        parse_mode="HTML"
    )


async def send_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_alerts_by_line = get_user_alerts(context.bot_data["supabase"],
                                          update.effective_user.id)
    alert_icon = {
        "danger": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅"
    }
    for line in user_alerts_by_line:
        msg = f"🚆 <b>{line}</b>\n"
        for alert in user_alerts_by_line[line]:
            msg += f"\n🛤️ <b>{alert['title']}</b>\n" if alert["title"] else "\n"
            msg += f"{alert_icon.get(alert['type'], 'ℹ️')} {alert['description']}\n" if alert["description"] else ""
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode="HTML"
        )


async def add_line(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    available_lines = get_available_lines(context.bot_data["supabase"], update.effective_user.id)
    if not available_lines:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No hay líneas disponibles para agregar."
        )
        return    
    
    keyboard = []
    for line in available_lines:
        keyboard.append([InlineKeyboardButton(
            text=line["name"],
            callback_data=f"add_line:{line['id']}:{line['name']}"
        )])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="➕ <b>Selecciona una línea para agregar:</b>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def remove_line(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_lines = get_user_lines(context.bot_data["supabase"], update.effective_user.id)
    if not user_lines:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No tenés líneas seleccionadas para eliminar."
        )
        return
    
    keyboard = []
    for line in user_lines:
        keyboard.append([InlineKeyboardButton(
            text=line["name"], 
            callback_data=f"remove_line:{line['id']}:{line['name']}"
        )])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="➖ <b>Selecciona una línea para eliminar:</b>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def handle_add_line_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, line_id, line_name = query.data.split(":", 2)

    add_user_line(context.bot_data["supabase"], update.effective_user.id, line_id)
    await query.edit_message_text(
        text=f"➕ <b>¡{line_name} agregada!</b>\n\nUsá /lines para ver todas tus líneas seleccionadas.",
        parse_mode="HTML"
    )


async def handle_remove_line_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, line_id, line_name = query.data.split(":", 2)

    remove_user_line(context.bot_data["supabase"], update.effective_user.id, line_id)
    await query.edit_message_text(
        text=f"➖ <b>¡{line_name} eliminada!</b>\n\nUsá /lines para ver todas tus líneas seleccionadas.",
        parse_mode="HTML"
    )
