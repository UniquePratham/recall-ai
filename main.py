"""
Main entry point for Recall AI bot
"""
import asyncio
import sys
import os
import time
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from handlers import (
    start, help_command, remember_command, search_command, talk_command,
    handle_document, handle_photo, handle_audio, handle_text,
    handle_ask, activate_callback, activate_command,
    handle_license_key, check_license, forget_command, forgetall_command
)
from config import config
from logging_config import setup_logging

logger = setup_logging()

# Health check endpoint for hosting / monitoring


async def health_check(request):
    """Health check endpoint for cloud deployment monitoring"""
    return web.json_response({
        "status": "healthy",
        "timestamp": time.time(),
        "service": "recall-ai-bot",
        "version": "1.0.0"
    })


async def start_health_server():
    """Start health check server for hosting and uptime monitoring"""
    try:
        port = int(os.getenv('PORT', 8000))
        app = web.Application()
        app.router.add_get('/health', health_check)
        app.router.add_get('/', health_check)  # Root endpoint for basic checks

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"✅ Health check server started on port {port}")
    except Exception as e:
        logger.warning(f"Failed to start health check server: {e}")


async def main() -> None:
    """Main application entry point"""
    # Validate configuration
    config_errors = config.validate()
    if config_errors:
        logger.error("Configuration errors: " + ", ".join(config_errors))
        sys.exit(1)

    logger.info("🚀 Starting Recall AI bot...")

    # Create application
    application = Application.builder().token(config.app.bot_token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("remember", remember_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("talk", talk_command))
    application.add_handler(CommandHandler("check_license", check_license))
    application.add_handler(CommandHandler("ask", handle_ask))
    application.add_handler(CommandHandler("activate", activate_command))
    application.add_handler(CommandHandler("forget", forget_command))
    application.add_handler(CommandHandler("forgetall", forgetall_command))
    application.add_handler(CallbackQueryHandler(
        activate_callback, pattern='^activate$'))

    # Message handlers
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'^[A-Z0-9]{16}$'),
        handle_license_key
    ))
    application.add_handler(MessageHandler(
        filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(
        filters.AUDIO | filters.VOICE, handle_audio))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text))

    # --- Health Server Setup ---
    port = int(os.getenv('PORT', 8000))
    health_app = web.Application()
    health_app.router.add_get('/health', health_check)
    health_app.router.add_get('/', health_check)
    runner = web.AppRunner(health_app)

    try:
        # --- Start Services ---
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"✅ Health check server started on port {port}")

        # Initialize and start the bot in a non-blocking way
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        logger.info("🤖 Bot is running! Press Ctrl-C to stop.")

        # Keep the script running until interrupted
        while True:
            await asyncio.sleep(3600)

    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot is shutting down...")
    except Exception as e:
        logger.error(f"💥 Unexpected error in main loop: {e}", exc_info=True)
    finally:
        # --- Stop Services Gracefully ---
        if application.updater and application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
        logger.info("✅ Bot has been shut down.")

        await runner.cleanup()
        logger.info("✅ Health check server has been shut down.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application terminated.")
