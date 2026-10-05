import research
from request import ResearchRequest
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import config
from core import database
from ui import format as fmt
from ui import history
import utils

logger = utils.logger


# --- Command handlers ---------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None:
        return
    await update.message.reply_text(
        "Welcome to ResearchBot! Send /research <topic> to start a new research task."
    )


async def research_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /research command with optional depth flag."""
    if update.effective_user is None:
        return

    if not context.args:
        telegram_id = str(update.effective_user.id)
        database.set_user_state(telegram_id, 'awaiting_topic')
        await update.message.reply_text(
            "Send me your research topic.\n"
            "You can also choose depth: /research --quick <topic>, "
            "/research --deep <topic>, /research --exhaustive <topic>"
        )
        return

    args = list(context.args)
    depth = "standard"
    if args and args[0].startswith("--"):
        flag = args[0].lstrip("-").lower()
        if flag in ("quick", "standard", "deep", "exhaustive"):
            depth = flag
            args = args[1:]
        else:
            await update.message.reply_text(f"Unknown depth: {args[0]}")
            return

    topic = " ".join(args).strip()
    if not topic:
        await update.message.reply_text("Topic cannot be empty.")
        return

    await start_new_research(update, context, topic, depth=depth)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages (for pending topics)."""
    if update.effective_user is None:
        return

    user = update.effective_user
    telegram_id = str(user.id)
    state = database.get_user_state(telegram_id)
    if state and state['state'] == 'awaiting_topic':
        topic = update.message.text.strip()
        if topic:
            database.clear_user_state(telegram_id)
            await start_new_research(update, context, topic, depth="standard")
        else:
            await update.message.reply_text("Please send a valid topic.")


async def start_new_research(update, context, topic, depth="standard"):
    """Create a research job and start worker with progress callback."""
    user = update.effective_user
    telegram_id = str(user.id)

    request = ResearchRequest(topic=topic, depth=depth)

    progress_message = await update.message.reply_text(
        f"🔎 Research started ({depth} depth)...\nStatus: initializing..."
    )

    loop = asyncio.get_running_loop()

    def progress_callback(research_id, stage):
        message_text = fmt.format_progress(stage)

        async def update_message():
            try:
                await progress_message.edit_text(
                    f"🔎 Research {research_id} status:\n{message_text}"
                )
            except Exception as e:
                logger.error(f"Failed to update progress message: {e}")

        asyncio.run_coroutine_threadsafe(update_message(), loop)

    research_id = research.research(request, telegram_id, progress_callback)

    await progress_message.edit_text(
        f"🔎 Research {research_id} ({depth} depth):\n{fmt.format_progress('analysis')}"
    )


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None:
        return

    user = update.effective_user
    telegram_id = str(user.id)
    user_id = database.get_or_create_user(telegram_id)
    research_list = database.get_user_research(user_id)
    text = history.format_history(research_list)
    await update.message.reply_text(text)


async def get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None:
        return

    user = update.effective_user
    telegram_id = str(user.id)
    if not context.args:
        await update.message.reply_text("Usage: /get <research_id>")
        return
    try:
        research_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid research ID.")
        return

    user_id = database.get_or_create_user(telegram_id)
    research = database.get_research(research_id)
    if not research or research['user_id'] != user_id:
        await update.message.reply_text("Research not found.")
        return

    answer = database.get_answer(research_id)
    if answer:
        for msg in fmt.split_message(answer['content']):
            await update.message.reply_text(msg, parse_mode=None)
    else:
        await update.message.reply_text("No answer available for this research.")


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None:
        return

    user = update.effective_user
    telegram_id = str(user.id)
    user_id = database.get_or_create_user(telegram_id)

    research_list = database.get_user_research(user_id)
    for r in research_list:
        if r['status'] not in ('completed', 'failed', 'cancelled'):
            database.set_cancel_requested(r['id'], True)
            topic = (r['topic'] or '').strip()
            short_topic = topic if len(topic) <= 60 else topic[:57] + "..."
            await update.message.reply_text(
                f"🛑 Cancellation requested for research {r['id']}.\n"
                f"Topic: {short_topic}\n"
                f"Current stage: {r['current_stage'] or 'unknown'}\n\n"
                "The worker will stop at the next checkpoint. "
                "Partial research data remains in your history."
            )
            return

    await update.message.reply_text("No active research to cancel.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


# --- Entry point --------------------------------------------------------

def main():
    database.init_db()

    recovered = database.recover_stale_jobs(
        max_age_minutes=config.RECOVERY_MAX_AGE_MINUTES
    )
    if recovered:
        logger.warning(f"Recovered {recovered} stale research job(s)")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("research", research_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("get", get_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_message
    ))
    app.add_error_handler(error_handler)

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()