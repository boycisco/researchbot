import research
from request import ResearchRequest
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import config
import database
import worker
from ui import format as fmt
from ui import history
import utils

logger = utils.logger

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to ResearchBot! Send /research <topic> to start a new research task."
    )

async def research_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /research command with optional topic."""
    user = update.effective_user
    telegram_id = str(user.id)
    # Check if there is an argument
    if context.args:
        topic = ' '.join(context.args)
        await start_new_research(update, context, topic)
    else:
        # Ask for topic
        await update.message.reply_text("Please send me your research topic.")
        # Set state to await topic
        database.set_user_state(telegram_id, 'awaiting_topic')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages (for pending topics)."""
    user = update.effective_user
    telegram_id = str(user.id)
    state = database.get_user_state(telegram_id)
    if state and state['state'] == 'awaiting_topic':
        topic = update.message.text.strip()
        if topic:
            database.clear_user_state(telegram_id)
            await start_new_research(update, context, topic)
        else:
            await update.message.reply_text("Please send a valid topic.")
    # else ignore

async def start_new_research(update, context, topic):
    """Create a research job and start worker with progress callback."""
    user = update.effective_user
    telegram_id = str(user.id)

    # Build a ResearchRequest with defaults
    request = ResearchRequest(topic=topic)

    # Send initial message and keep a reference to it
    progress_message = await update.message.reply_text(
        f"🔎 Research started (ID: pending)...\nStatus: initializing..."
    )

    # Capture the running event loop (main thread)
    loop = asyncio.get_running_loop()

    def progress_callback(research_id, stage):
        message_text = fmt.format_progress(stage)

        async def update_message():
            try:
                await progress_message.edit_text(
                    f"🔎 Research {research_id} status:\n{message_text}"
                )
            except Exception as e:
                utils.logger.error(f"Failed to update progress message: {e}")

        asyncio.run_coroutine_threadsafe(update_message(), loop)

    # Start the research via the application layer
    research_id = research.research(request, telegram_id, progress_callback)

    # Update the initial message with the actual research ID
    await progress_message.edit_text(
        f"🔎 Research {research_id} status:\n{fmt.format_progress('analysis')}"
    )

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = str(user.id)
    user_id = database.get_or_create_user(telegram_id)
    research_list = database.get_user_research(user_id)
    if not research_list:
        await update.message.reply_text("You have no research history.")
        return
    # Format history (simplified)
    lines = []
    for r in research_list[:10]:
        lines.append(f"ID {r['id']}: {r['topic'][:50]} - {r['status']}")
    await update.message.reply_text("\n".join(lines))

async def get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    # Check ownership
    user_id = database.get_or_create_user(telegram_id)
    research = database.get_research(research_id)
    if not research or research['user_id'] != user_id:
        await update.message.reply_text("Research not found.")
        return
    answer = database.get_answer(research_id)
    if answer:
        # Send answer (split if too long)
        for msg in fmt.split_message(answer['content']):
            await update.message.reply_text(msg, parse_mode=None)  # plain text
    else:
        await update.message.reply_text("No answer available for this research.")

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = str(user.id)
    user_id = database.get_or_create_user(telegram_id)
    # Find active research for user
    research_list = database.get_user_research(user_id)
    for r in research_list:
        if r['status'] not in ('completed', 'failed', 'cancelled'):
            database.set_cancel_requested(r['id'], True)
            await update.message.reply_text(f"Cancellation requested for research {r['id']}.")
            return
    await update.message.reply_text("No active research to cancel.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    # Initialize database
    database.init_db()
    # Build application
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("research", research_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("get", get_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    # Start bot
    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()