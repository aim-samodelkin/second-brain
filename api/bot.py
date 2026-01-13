"""
Second Brain Telegram Bot
With intelligent agents for notes, Q&A, and research
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

logger = logging.getLogger(__name__)

# Bot instance (will be created on startup)
bot_app: Optional[Application] = None

# Agents and director (initialized on startup)
director = None
llm_manager = None
vector_store = None
metadata_generator = None

# Import settings and couchdb client from main
# This is done at runtime to avoid circular imports


def get_settings():
    from main import settings
    return settings


def get_couchdb():
    from main import couchdb
    return couchdb


# ============================================
# TELEGRAM HANDLERS
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    settings = get_settings()

    if user.id != settings.telegram_admin_id:
        await update.message.reply_text(
            "This bot works only for the Second Brain owner."
        )
        return

    keyboard = [
        [InlineKeyboardButton("🔍 Research Topic", callback_data="research")],
        [InlineKeyboardButton("📝 Recent Notes", callback_data="recent")],
        [InlineKeyboardButton("📊 Daily Summary", callback_data="summary")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Hi, {user.first_name}! I'm your intelligent Second Brain bot 🧠\n\n"
        "I can:\n"
        "• 📝 Save notes with smart categorization\n"
        "• ❓ Answer questions from your knowledge base\n"
        "• 🔍 Research topics deeply\n\n"
        "Just send me:\n"
        "• Any text → I'll save it as a smart note\n"
        "• A question → I'll search and answer\n"
        "• Use Research button → Deep topic analysis",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "*Second Brain Bot*\n\n"
        "*Commands:*\n"
        "/start - main menu\n"
        "/note <text> - create a note\n"
        "/recent - last 10 notes\n"
        "/summary - daily summary\n"
        "/search <query> - search notes\n"
        "/help - this help\n\n"
        "Just send any text and it will be saved as a note in Inbox folder.",
        parse_mode="Markdown"
    )


async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /note command - create quick note"""
    settings = get_settings()
    if update.effective_user.id != settings.telegram_admin_id:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /note <note text>\n"
            "Or just send me text without a command."
        )
        return

    content = " ".join(context.args)
    await save_quick_note(update, content)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages via intelligent agents"""
    global director
    
    settings = get_settings()
    if update.effective_user.id != settings.telegram_admin_id:
        return

    content = update.message.text
    if content.startswith("/"):
        return  # Ignore commands

    # If agents are not initialized, fall back to simple note saving
    if not director:
        logger.warning("Director not initialized, falling back to simple note")
        await save_quick_note(update, content)
        return
    
    try:
        # Build context for agents
        user_context = {
            'user_id': update.effective_user.id,
            'username': update.effective_user.username or update.effective_user.first_name,
            'awaiting_research': context.user_data.get('awaiting_research', False)
        }
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        # Route message through director
        response = await director.route_message(content, user_context)
        
        # Clear research mode if it was active
        if context.user_data.get('awaiting_research'):
            context.user_data['awaiting_research'] = False
        
        # Send response
        await update.message.reply_text(
            response.text,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error processing your message: {str(e)}"
        )


async def save_quick_note(update: Update, content: str):
    """Save content as a quick note in CouchDB"""
    couchdb = get_couchdb()

    try:
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Inbox/Telegram_{timestamp}.md"

        # Format content with frontmatter
        username = update.effective_user.username or update.effective_user.first_name
        note_content = f"""---
created: {datetime.now().isoformat()}
source: telegram
from: {username}
---

{content}
"""

        # Create document in Livesync format
        doc = {
            "_id": filename,
            "path": filename,
            "data": note_content,
            "type": "leaf",
            "mtime": int(datetime.now().timestamp() * 1000),
            "ctime": int(datetime.now().timestamp() * 1000),
            "size": len(note_content)
        }

        result = await couchdb.create_document(doc)

        await update.message.reply_text(
            f"Note saved!\n"
            f"File: `{filename}`",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error saving note: {e}")
        await update.message.reply_text(
            f"Error saving note: {str(e)}"
        )


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recent command - show recent notes"""
    settings = get_settings()
    if update.effective_user.id != settings.telegram_admin_id:
        return

    couchdb = get_couchdb()

    try:
        docs = await couchdb.get_recent_documents(10)

        if not docs:
            await update.message.reply_text("No notes yet.")
            return

        text = "*Recent notes:*\n\n"
        for doc in docs:
            path = doc.get("path", doc["_id"])
            mtime = doc.get("mtime", 0)
            if mtime:
                dt = datetime.fromtimestamp(mtime / 1000)
                time_str = dt.strftime("%d.%m %H:%M")
            else:
                time_str = "—"

            # Truncate long paths
            if len(path) > 35:
                path = "..." + path[-32:]

            text += f"• `{path}` ({time_str})\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error getting recent notes: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /summary command - daily summary"""
    settings = get_settings()
    if update.effective_user.id != settings.telegram_admin_id:
        return

    couchdb = get_couchdb()

    try:
        stats = await couchdb.get_stats()
        recent = await couchdb.get_recent_documents(20)

        today = datetime.now().date()
        new_today = sum(
            1 for doc in recent
            if doc.get("mtime") and
            datetime.fromtimestamp(doc["mtime"] / 1000).date() == today
        )

        text = f"*Summary for {today.strftime('%d.%m.%Y')}*\n\n"
        text += f"Total notes: {stats.get('doc_count', 0)}\n"
        text += f"New/modified today: {new_today}\n\n"

        if recent:
            text += "*Recent changes:*\n"
            for doc in recent[:5]:
                path = doc.get("path", doc["_id"])
                if len(path) > 30:
                    path = "..." + path[-27:]
                text += f"• {path}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    settings = get_settings()
    if update.effective_user.id != settings.telegram_admin_id:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /search <query>\n"
            "Example: /search project"
        )
        return

    query = " ".join(context.args)
    couchdb = get_couchdb()

    try:
        results = await couchdb.search_documents(query, 10)

        if not results:
            await update.message.reply_text(
                f"No results for \"{query}\"."
            )
            return

        text = f"*Search results for \"{query}\":*\n\n"
        for doc in results:
            path = doc.get("path", doc["_id"])
            if len(path) > 35:
                path = "..." + path[-32:]

            snippet = doc.get("data", "")[:80]
            if len(doc.get("data", "")) > 80:
                snippet += "..."

            # Clean up snippet
            snippet = snippet.replace("\n", " ").replace("---", "").strip()

            text += f"• `{path}`\n{snippet}\n\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text(f"Search error: {str(e)}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
    query = update.callback_query
    await query.answer()

    settings = get_settings()
    if update.effective_user.id != settings.telegram_admin_id:
        return

    if query.data == "research":
        # Activate Research mode
        context.user_data['awaiting_research'] = True
        await query.edit_message_text(
            "🔍 **Research Mode Activated**\n\n"
            "Send me a topic to research, and I'll:\n"
            "• Analyze all related notes\n"
            "• Find connections and patterns\n"
            "• Provide deep insights\n\n"
            "Example: \"machine learning deployment\"\n\n"
            "Send /start to cancel.",
            parse_mode="Markdown"
        )
    
    elif query.data == "recent":
        await recent_command(update, context)

    elif query.data == "summary":
        await summary_command(update, context)

    elif query.data == "help":
        await query.edit_message_text(
            "🧠 **Second Brain Bot Help**\n\n"
            "**Intelligent Features:**\n"
            "• Send any text → Smart note with auto-categorization\n"
            "• Ask a question → AI-powered answer from your notes\n"
            "• Research button → Deep topic analysis\n\n"
            "**Commands:**\n"
            "/start - main menu\n"
            "/recent - last 10 notes\n"
            "/summary - daily summary\n"
            "/search <query> - search notes\n"
            "/help - this help\n\n"
            "The bot automatically detects:\n"
            "❓ Questions → Q&A mode\n"
            "📝 Statements → Note taking\n"
            "🔍 Research → Deep analysis",
            parse_mode="Markdown"
        )


# ============================================
# BOT INITIALIZATION
# ============================================

async def start_bot():
    """Initialize and start the Telegram bot with intelligent agents"""
    global bot_app, director, llm_manager, vector_store, metadata_generator

    settings = get_settings()
    couchdb = get_couchdb()
    logger.info("Starting Telegram bot with intelligent agents...")

    # Initialize LLM and Vector Store
    try:
        from llm.manager import LLMManager, LLMSettings
        from vector_store import VectorStoreClient, VectorStoreSettings
        from metadata_generator import MetadataGenerator
        from agents.director import MessageDirector
        from agents.note_taker import SmartNoteTaker
        from agents.qa_agent import QAAgent
        from agents.research_agent import ResearchAgent
        
        # Initialize LLM Manager
        llm_settings = LLMSettings()
        llm_manager = LLMManager(llm_settings)
        logger.info(f"LLM Manager initialized with providers: {llm_manager.list_providers()}")
        
        # Initialize Vector Store
        vector_settings = VectorStoreSettings()
        vector_store = VectorStoreClient(vector_settings)
        await vector_store.initialize()
        logger.info("Vector Store initialized")
        
        # Initialize Metadata Generator
        metadata_generator = MetadataGenerator(llm_manager)
        logger.info("Metadata Generator initialized")
        
        # Initialize Director
        director = MessageDirector(llm_manager, couchdb, vector_store)
        
        # Register agents
        note_taker = SmartNoteTaker(llm_manager, couchdb, vector_store, metadata_generator)
        qa_agent = QAAgent(llm_manager, couchdb, vector_store)
        research_agent = ResearchAgent(llm_manager, couchdb, vector_store)
        
        director.register_agent(note_taker)
        director.register_agent(qa_agent)
        director.register_agent(research_agent)
        
        logger.info(f"Registered agents: {director.list_agents()}")
        
    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}", exc_info=True)
        logger.warning("Bot will run in basic mode without intelligent agents")
        director = None

    # Create application
    bot_app = Application.builder().token(settings.telegram_bot_token).build()

    # Add handlers
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("note", note_command))
    bot_app.add_handler(CommandHandler("recent", recent_command))
    bot_app.add_handler(CommandHandler("summary", summary_command))
    bot_app.add_handler(CommandHandler("search", search_command))
    bot_app.add_handler(CallbackQueryHandler(button_callback))
    bot_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))

    # Start polling in background
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)

    logger.info("Telegram bot started successfully")


async def stop_bot():
    """Stop the Telegram bot"""
    global bot_app
    if bot_app:
        logger.info("Stopping Telegram bot...")
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        logger.info("Telegram bot stopped")
