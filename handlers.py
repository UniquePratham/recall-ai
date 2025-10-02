"""
Simple handlers for Recall AI Telegram bot
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from processors import (
    process_document,
    process_photo,
    process_audio,
    process_text,
    process_url
)
from utils import search_cache_first, delete_memories_by_terms, clear_all_memories
from utils import chat_completion
from database import is_user_activated, activate_user
from validators import validate_license_key
from logging_config import setup_logging, log_user_action, log_error
from config import config
from cache_manager import cache_manager

logger = setup_logging()

MODE_KEYBOARD_LAYOUT = [["/remember", "/search",
                         "/talk"], ["/forget", "/forgetall", "/help"]]


def get_mode_keyboard() -> ReplyKeyboardMarkup:
    """Build the main mode selection keyboard"""
    return ReplyKeyboardMarkup(MODE_KEYBOARD_LAYOUT, resize_keyboard=True)


def is_owner(user_id: int) -> bool:
    owner_id = config.app.owner_telegram_id
    return owner_id != 0 and user_id == owner_id


async def ensure_owner_and_activation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure the user is the owner and has an activated account"""
    user = update.effective_user

    if not is_owner(user.id):
        if update.message:
            await update.message.reply_text(
                "🔒 This Recall AI instance is private. Access is limited to the owner.",
                reply_markup=ReplyKeyboardRemove()
            )
        return False

    if not await is_user_activated(user.id):
        if update.message:
            await update.message.reply_text(
                "🔑 Your account isn't activated yet. Use /activate with your license key.",
                reply_markup=ReplyKeyboardRemove()
            )
        return False

    return True


def reset_conversation(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("conversation_history", None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initialize the bot"""
    user = update.effective_user
    if not is_owner(user.id):
        await update.message.reply_text(
            "🔒 This Recall AI instance is private. Access is limited to the owner.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    if await is_user_activated(user.id):
        # Restore last mode if available
        last_mode = cache_manager.get_user_mode(user.id)
        if last_mode:
            context.user_data["mode"] = last_mode
            reset_conversation(context)
            await update.message.reply_text(
                f"🚀 Welcome back! Restored your last mode: **{last_mode}**\n\n"
                "• /remember – store new memories (text, files, photos, audio)\n"
                "• /search – ask questions about what you've saved\n"
                "• /talk – have a conversation with access to recent search context",
                reply_markup=get_mode_keyboard(),
                parse_mode='Markdown'
            )
        else:
            context.user_data.setdefault("mode", None)
            reset_conversation(context)
            await update.message.reply_text(
                "Welcome back! Choose a mode to get started:\n\n"
                "• /remember – store new memories (text, files, photos, audio)\n"
                "• /search – ask questions about what you've saved\n"
                "• /talk – have a conversation without saving data",
                reply_markup=get_mode_keyboard()
            )
    else:
        keyboard = [[InlineKeyboardButton(
            "Activate Recall ✨", callback_data='activate')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Welcome to Recall AI! Activate your account with your license key to begin.",
            reply_markup=reply_markup
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information"""
    help_text = (
        "🧠 **Recall AI - Personal Memory Assistant**\n\n"
        "**Core modes:**\n"
        "• `/remember` – Save new files, notes, photos, or audio.\n"
        "• `/search` – Ask questions about what you've saved.\n"
        "• `/talk` – Chat freely without storing anything.\n\n"
        "**Memory management:**\n"
        "• `/forget` – Delete specific memories by search terms.\n"
        "• `/forgetall` – Clear all memories and cache.\n\n"
        "**Other commands:**\n"
        "• `/start` – Show the main menu.\n"
        "• `/help` – Display this help message.\n"
        "• `/activate <license_key>` – Activate your account (owner only).\n"
        "• `/ask <question>` – Quick search shortcut (same as `/search`).\n\n"
        "**Tips:**\n"
        "1. Switch to `/remember` before sending content you want to store.\n"
        "2. Use `/search` for knowledge-base queries.\n"
        "3. `/talk` is great for brainstorming—nothing is saved."
    )
    await update.message.reply_text(help_text, reply_markup=get_mode_keyboard())


async def remember_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_owner_and_activation(update, context):
        return

    user_id = update.effective_user.id
    cache_manager.set_user_mode(user_id, "remember")
    context.user_data["mode"] = "remember"
    reset_conversation(context)
    await update.message.reply_text(
        "📝 Remember mode activated.\n"
        "Send any text, document, photo, or audio and I'll store it in your knowledge base.",
        reply_markup=get_mode_keyboard()
    )
    log_user_action(logger, update.effective_user.id,
                    update.effective_user.username or "unknown", "mode_remember")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_owner_and_activation(update, context):
        return

    user_id = update.effective_user.id
    cache_manager.set_user_mode(user_id, "search")
    context.user_data["mode"] = "search"
    reset_conversation(context)
    await update.message.reply_text(
        "🔍 Search mode activated.\n"
        "Type your question and I'll look through your saved memories.",
        reply_markup=get_mode_keyboard()
    )
    log_user_action(logger, update.effective_user.id,
                    update.effective_user.username or "unknown", "mode_search")


async def talk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_owner_and_activation(update, context):
        return

    user_id = update.effective_user.id
    cache_manager.set_user_mode(user_id, "talk")
    context.user_data["mode"] = "talk"
    reset_conversation(context)

    # Get recent search context for enhanced chat
    username = update.effective_user.username or str(user_id)
    search_context = cache_manager.get_search_context_for_chat(username)

    if search_context:
        context.user_data["search_context"] = search_context
        await update.message.reply_text(
            "💬 Talk mode activated.\n"
            "Chat with me! I have access to your recent search results for context.",
            reply_markup=get_mode_keyboard()
        )
    else:
        await update.message.reply_text(
            "💬 Talk mode activated.\n"
            "Chat with me! (Use /search first to give me context about your memories)",
            reply_markup=get_mode_keyboard()
        )
    log_user_action(logger, update.effective_user.id,
                    update.effective_user.username or "unknown", "mode_talk")


async def check_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner-only debug command to check a provided license key against configured key.
    Usage: /check_license <key>
    This will NOT reveal the full configured key; it returns a masked preview and whether it matches.
    """
    user = update.effective_user
    owner_id = config.app.owner_telegram_id
    if user.id != owner_id:
        await update.message.reply_text("🔒 Only the owner may run this command.")
        return

    if not context.args:
        # Show masked configured key info only
        configured = (config.app.license_key or '').strip()
        if not configured:
            await update.message.reply_text("⚠️ No LICENSE_KEY is configured in the environment.")
            return

        masked = configured[:4] + '*' * \
            max(0, len(configured) - 8) + configured[-4:]
        await update.message.reply_text(f"Configured LICENSE_KEY: {masked} (length={len(configured)})")
        return

    provided = context.args[0].upper().strip()
    configured = (config.app.license_key or '').upper().strip()
    if not configured:
        await update.message.reply_text("⚠️ No LICENSE_KEY is configured in the environment.")
        return

    match = provided == configured
    masked = configured[:4] + '*' * \
        max(0, len(configured) - 8) + configured[-4:]
    await update.message.reply_text(
        f"Provided key matches configured: {'✅' if match else '❌'}\nConfigured: {masked} (length={len(configured)})"
    )


async def activate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle activation button"""
    query = update.callback_query
    await query.answer()
    # Only owner can trigger activation
    user = update.effective_user
    owner_id = config.app.owner_telegram_id
    if user.id != owner_id:
        await query.edit_message_text("🔒 Only the owner can activate this bot.")
        return

    await query.edit_message_text("Please enter your 16-character license key:")
    context.user_data['awaiting_license'] = True


async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /activate command"""
    user = update.effective_user
    owner_id = config.app.owner_telegram_id
    # Only owner can activate
    if user.id != owner_id:
        await update.message.reply_text("🔒 Only the owner may activate this bot.")
        return

    if await is_user_activated(user.id):
        await update.message.reply_text("✅ Your account is already activated!")
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide your license key: `/activate YOUR_LICENSE_KEY`"
        )
        return

    license_key = context.args[0].upper().strip()

    # Check against configured license key
    configured_key = config.app.license_key.upper().strip()
    if not configured_key:
        await update.message.reply_text("⚠️ License system is not configured. Please set LICENSE_KEY in environment.")
        return

    if license_key != configured_key:
        await update.message.reply_text("❌ License key does not match the configured key.")
        return

    if not validate_license_key(license_key):
        await update.message.reply_text(
            "❌ Invalid license key format. Must be 16 characters (letters and numbers)."
        )
        return

    success, message = await activate_user(user.id, user.username, license_key)

    if success:
        context.user_data.pop('awaiting_license', None)
        context.user_data['mode'] = None
        reset_conversation(context)
        await update.message.reply_text(
            f"✅ {message}\n\nWelcome to Recall AI! Choose a mode to begin.",
            reply_markup=get_mode_keyboard()
        )
        log_user_action(logger, user.id,
                        user.username or "unknown", "account_activated")
    else:
        await update.message.reply_text(f"❌ {message}")


async def handle_license_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle license key input"""
    if not context.user_data.get('awaiting_license'):
        await handle_text(update, context)
        return

    user = update.effective_user
    owner_id = config.app.owner_telegram_id
    if user.id != owner_id:
        await update.message.reply_text("🔒 Only the owner may enter the license key.")
        return

    license_key = update.message.text.upper().strip()

    configured_key = config.app.license_key.upper().strip()
    if not configured_key:
        await update.message.reply_text("⚠️ License system is not configured. Please set LICENSE_KEY in environment.")
        return

    if license_key != configured_key:
        await update.message.reply_text("❌ License key does not match the configured key.")
        return

    if not validate_license_key(license_key):
        await update.message.reply_text(
            "❌ Invalid format. License key must be 16 characters (letters and numbers)."
        )
        return

    success, message = await activate_user(user.id, user.username, license_key)

    if success:
        context.user_data['awaiting_license'] = False
        context.user_data['mode'] = None
        reset_conversation(context)
        await update.message.reply_text(
            f"✅ {message}\n\nYou can now start using Recall AI! Choose a mode to begin.",
            reply_markup=get_mode_keyboard()
        )
        log_user_action(logger, user.id,
                        user.username or "unknown", "account_activated")
    else:
        await update.message.reply_text(f"❌ {message}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads in remember mode"""
    if not await ensure_owner_and_activation(update, context):
        return

    user = update.effective_user
    if context.user_data.get("mode") != "remember":
        await update.message.reply_text(
            "📄 Switch to /remember mode before sending documents you want to save.",
            reply_markup=get_mode_keyboard()
        )
        return

    try:
        doc = update.message.document
        if not doc:
            await update.message.reply_text("❌ No document found in the message.")
            return

        await update.message.reply_text("📄 Processing document...")
        result = await process_document(doc, user.username or str(user.id))
        await update.message.reply_text(result or "✅ Document processed and stored!",
                                        reply_markup=get_mode_keyboard())
        log_user_action(logger, user.id,
                        user.username or "unknown", "document_processed")
    except Exception as e:
        log_error(
            logger, e, {"operation": "handle_document", "user_id": user.id})
        await update.message.reply_text("❌ Failed to process document. Please try again.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads in remember mode"""
    if not await ensure_owner_and_activation(update, context):
        return

    user = update.effective_user
    if context.user_data.get("mode") != "remember":
        await update.message.reply_text(
            "�️ Switch to /remember mode before sending photos you want to save.",
            reply_markup=get_mode_keyboard()
        )
        return

    try:
        if not update.message.photo:
            await update.message.reply_text("❌ No photo found in the message.")
            return

        photo = update.message.photo[-1]
        await update.message.reply_text("🖼️ Analyzing image...")
        result = await process_photo(photo, user.username or str(user.id))
        await update.message.reply_text(result or "✅ Image analyzed and stored!",
                                        reply_markup=get_mode_keyboard())
        log_user_action(logger, user.id,
                        user.username or "unknown", "photo_processed")
    except Exception as e:
        log_error(logger, e, {"operation": "handle_photo", "user_id": user.id})
        await update.message.reply_text("❌ Failed to process image. Please try again.")


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio uploads in remember mode"""
    if not await ensure_owner_and_activation(update, context):
        return

    user = update.effective_user
    if context.user_data.get("mode") != "remember":
        await update.message.reply_text(
            "🎵 Switch to /remember mode before sending audio you want to save.",
            reply_markup=get_mode_keyboard()
        )
        return

    try:
        audio = update.message.audio or update.message.voice
        if not audio:
            await update.message.reply_text("❌ No audio message detected.")
            return

        await update.message.reply_text("🎵 Transcribing audio...")
        result = await process_audio(audio, user.username or str(user.id))
        await update.message.reply_text(result or "✅ Audio transcribed and stored!",
                                        reply_markup=get_mode_keyboard())
        log_user_action(logger, user.id,
                        user.username or "unknown", "audio_processed")
    except Exception as e:
        log_error(logger, e, {"operation": "handle_audio", "user_id": user.id})
        await update.message.reply_text("❌ Failed to process audio. Please try again.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages based on the selected mode"""
    if context.user_data.get('awaiting_license'):
        await update.message.reply_text("� Please enter your 16-character license key to activate the bot.")
        return

    if not await ensure_owner_and_activation(update, context):
        return

    user = update.effective_user
    text = (update.message.text or "").strip()

    if not text:
        await update.message.reply_text("I couldn't detect any text. Please try again.")
        return

    # Handle forget confirmations
    if context.user_data.get('pending_forget'):
        await handle_forget_confirmation(update, context, text)
        return

    if context.user_data.get('pending_forget_all'):
        await handle_forget_all_confirmation(update, context, text)
        return

    mode = context.user_data.get("mode")
    try:
        if mode == "remember":
            if text.startswith(('http://', 'https://')):
                await update.message.reply_text("🌐 Processing URL...")
                result = await process_url(text, user.username or str(user.id))
            else:
                result = await process_text(text, user.username or str(user.id))

            await update.message.reply_text(result or "✅ Message stored!",
                                            reply_markup=get_mode_keyboard())
            log_user_action(logger, user.id,
                            user.username or "unknown", "text_processed")

        elif mode == "search":
            await handle_ask_internal(update, context, text)
            return

        elif mode == "talk":
            history = context.user_data.setdefault("conversation_history", [])
            history.append({"role": "user", "content": text})
            system_prompt = "You are Recall AI in talk mode. Have a friendly, concise conversation. Do not mention saving data."
            messages = [{"role": "system", "content": system_prompt}] + history
            reply = await chat_completion(messages, max_tokens=350)
            history.append({"role": "assistant", "content": reply})
            # Keep conversation history manageable
            if len(history) > 20:
                del history[:len(history) - 20]
            await update.message.reply_text(reply)
            log_user_action(logger, user.id,
                            user.username or "unknown", "talk_message")

        else:
            await update.message.reply_text(
                "Please choose a mode first using /remember, /search, or /talk.",
                reply_markup=get_mode_keyboard()
            )

    except Exception as e:
        log_error(logger, e, {"operation": "handle_text", "user_id": user.id})
        await update.message.reply_text("❌ Failed to process message. Please try again.")


async def handle_forget_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Handle confirmation for forget command"""
    user = update.effective_user
    pending = context.user_data.get('pending_forget')

    if not pending:
        return

    if text.upper().strip() == 'YES':
        try:
            await update.message.reply_text("🗑️ Deleting memories...")

            deleted_count, summary = await delete_memories_by_terms(
                pending['search_terms'],
                pending['username'],
                preview_only=False
            )

            # Clear related cache entries
            cache_manager.clear_user_search_cache(
                pending['username'], pending['search_terms'])

            await update.message.reply_text(
                f"✅ Successfully deleted {deleted_count} memories containing '{pending['search_terms']}'.\n\n"
                f"{summary}",
                reply_markup=get_mode_keyboard()
            )

            log_user_action(logger, user.id, pending['username'], "memories_deleted", {
                "terms": pending['search_terms'],
                "count": deleted_count
            })

        except Exception as e:
            log_error(
                logger, e, {"operation": "handle_forget_confirmation", "user_id": user.id})
            await update.message.reply_text("❌ Error deleting memories. Please try again.")
    else:
        await update.message.reply_text(
            "❌ Deletion cancelled. Your memories are safe.",
            reply_markup=get_mode_keyboard()
        )

    # Clear pending state
    context.user_data.pop('pending_forget', None)


async def handle_forget_all_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Handle confirmation for forget-all command"""
    user = update.effective_user
    pending = context.user_data.get('pending_forget_all')

    if not pending:
        return

    if text.strip() == 'DELETE ALL':
        try:
            await update.message.reply_text("🗑️ Deleting ALL memories and clearing cache...")

            deleted_count = await clear_all_memories(pending['username'], preview_only=False)

            # Clear all cache for this user
            cache_manager.clear_all_user_cache(pending['username'])

            await update.message.reply_text(
                f"✅ Successfully deleted ALL memories and cache:\n\n"
                f"• **{deleted_count} memories** deleted from database\n"
                f"• **All search cache** cleared\n\n"
                f"Your Recall AI is now completely reset.",
                reply_markup=get_mode_keyboard(),
                parse_mode='Markdown'
            )

            log_user_action(logger, user.id, pending['username'], "all_memories_deleted", {
                "count": deleted_count
            })

        except Exception as e:
            log_error(
                logger, e, {"operation": "handle_forget_all_confirmation", "user_id": user.id})
            await update.message.reply_text("❌ Error deleting memories. Please try again.")
    else:
        await update.message.reply_text(
            "❌ Deletion cancelled. Your memories are safe.\n\n"
            "(Note: You must type 'DELETE ALL' exactly to confirm)",
            reply_markup=get_mode_keyboard()
        )

    # Clear pending state
    context.user_data.pop('pending_forget_all', None)


async def handle_ask_internal(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str = None) -> None:
    """Internal ask handler"""
    user = update.effective_user

    try:
        if not query:
            query = ' '.join(context.args) if context.args else ""

        if not query.strip():
            await update.message.reply_text("🤔 Please provide a question: `/ask What did I learn about Python?`")
            return

        await update.message.reply_text("🧠 Searching your memories...")

        # Use cache-first search logic with appropriate limit
        limit = 10 if any(word in query.lower() for word in [
                          'all', 'list', 'every', 'entire', 'complete']) else 8
        result = await search_cache_first(query, user.username or str(user.id), limit)

        # Clean up the result formatting
        cleaned_result = result.strip()

        # Remove any remaining ** formatting artifacts
        cleaned_result = cleaned_result.replace(
            '**Your Question:**', '').replace('**Answer:**', '')
        cleaned_result = cleaned_result.replace('**', '').strip()

        # Format the response properly
        if cleaned_result:
            await update.message.reply_text(f"💡 {cleaned_result}", parse_mode='Markdown')
        else:
            await update.message.reply_text("🤔 I couldn't find relevant information for your query.")

        log_user_action(logger, user.id,
                        user.username or "unknown", "query_answered")

    except Exception as e:
        log_error(logger, e, {"operation": "handle_ask", "user_id": user.id})
        await update.message.reply_text("❌ Error searching memories. Please try again.")


async def handle_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask command"""
    if not await ensure_owner_and_activation(update, context):
        return

    context.user_data["mode"] = "search"
    reset_conversation(context)
    await handle_ask_internal(update, context)


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /forget command to delete specific memories"""
    if not await ensure_owner_and_activation(update, context):
        return

    user = update.effective_user
    username = user.username or str(user.id)

    if not context.args:
        await update.message.reply_text(
            "🗑️ **Forget specific memories**\n\n"
            "Usage: `/forget <search terms>`\n\n"
            "Example: `/forget python tutorial`\n\n"
            "This will search for memories containing those terms and ask for confirmation before deleting.",
            reply_markup=get_mode_keyboard(),
            parse_mode='Markdown'
        )
        return

    search_terms = ' '.join(context.args)

    try:
        await update.message.reply_text(f"🔍 Searching for memories containing: '{search_terms}'...")

        # Find matching memories
        matching_count, preview = await delete_memories_by_terms(search_terms, username, preview_only=True)

        if matching_count == 0:
            await update.message.reply_text(
                f"No memories found containing '{search_terms}'.",
                reply_markup=get_mode_keyboard()
            )
            return

        # Ask for confirmation
        confirmation_text = (
            f"⚠️ **Found {matching_count} memories to delete:**\n\n"
            f"{preview}\n\n"
            f"**Are you sure you want to delete these memories?**\n"
            f"Reply 'YES' to confirm or anything else to cancel."
        )

        await update.message.reply_text(confirmation_text, parse_mode='Markdown')
        context.user_data['pending_forget'] = {
            'search_terms': search_terms,
            'username': username,
            'count': matching_count
        }

        log_user_action(logger, user.id, username, "forget_search", {
                        "terms": search_terms, "count": matching_count})

    except Exception as e:
        log_error(
            logger, e, {"operation": "forget_command", "user_id": user.id})
        await update.message.reply_text("❌ Error searching for memories. Please try again.")


async def forgetall_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /forgetall command to clear all memories and cache"""
    if not await ensure_owner_and_activation(update, context):
        return

    user = update.effective_user
    username = user.username or str(user.id)

    try:
        # Get count of existing memories
        total_count = await clear_all_memories(username, preview_only=True)

        if total_count == 0:
            await update.message.reply_text(
                "No memories found to delete.",
                reply_markup=get_mode_keyboard()
            )
            return

        # Ask for confirmation
        confirmation_text = (
            f"⚠️ **WARNING: This will permanently delete ALL your memories!**\n\n"
            f"• **{total_count} memories** will be deleted from the database\n"
            f"• **All cached searches** will be cleared\n"
            f"• This action **cannot be undone**\n\n"
            f"**Are you absolutely sure?**\n"
            f"Reply 'DELETE ALL' (exactly) to confirm or anything else to cancel."
        )

        await update.message.reply_text(confirmation_text, parse_mode='Markdown')
        context.user_data['pending_forget_all'] = {
            'username': username,
            'count': total_count
        }

        log_user_action(logger, user.id, username,
                        "forget_all_requested", {"count": total_count})

    except Exception as e:
        log_error(
            logger, e, {"operation": "forget_all_command", "user_id": user.id})
        await update.message.reply_text("❌ Error checking memories. Please try again.")
