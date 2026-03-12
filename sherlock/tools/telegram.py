"""Telegram tools — send notifications and receive investigation requests."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from sherlock.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outbound: send notifications to the user
# ---------------------------------------------------------------------------


async def send_notification(message: str) -> None:
    """Send a text notification to the configured Telegram chat."""
    if not settings.telegram_configured:
        return

    try:
        bot = Bot(token=settings.telegram_bot_token)
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=message,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


async def send_report_file(file_path: str | Path, caption: str = "") -> None:
    """Send a report file directly to the Telegram chat."""
    if not settings.telegram_configured:
        return

    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Report file not found for Telegram delivery: {path}")
        return

    try:
        bot = Bot(token=settings.telegram_bot_token)
        with open(path, "rb") as f:
            await bot.send_document(
                chat_id=settings.telegram_chat_id,
                document=f,
                filename=path.name,
                caption=caption[:1024] if caption else f"📄 {path.name}",
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.warning(f"Telegram file send failed: {e}")


async def notify_investigation_started(query: str, task_count: int) -> None:
    """Notify that an investigation has kicked off."""
    await send_notification(
        f"🔍 *Investigation started*\n\n"
        f"_{query}_\n\n"
        f"📋 {task_count} sub-tasks planned"
    )


async def notify_task_completed(task_description: str, finding_count: int) -> None:
    """Notify that a sub-task has completed."""
    await send_notification(
        f"✅ *Sub-task completed*\n\n"
        f"{task_description}\n"
        f"📊 {finding_count} findings"
    )


async def notify_task_failed(task_description: str, error: str) -> None:
    """Notify that a sub-task failed."""
    await send_notification(
        f"⚠️ *Sub-task failed*\n\n"
        f"{task_description}\n"
        f"Error: `{error[:200]}`"
    )


async def notify_investigation_complete(
    query: str, finding_count: int, report_path: str | Path
) -> None:
    """Notify that the full investigation is done and deliver the report."""
    await send_notification(
        f"🎯 *Investigation complete*\n\n"
        f"_{query}_\n\n"
        f"📊 {finding_count} total findings\n"
        f"📄 Report attached below"
    )
    await send_report_file(report_path, caption=f"🔍 _{query}_")


# ---------------------------------------------------------------------------
# Inbound: Telegram bot that receives messages and kicks off investigations
# ---------------------------------------------------------------------------


def create_bot_application(
    on_investigate: callable | None = None,
) -> Application:
    """Create a Telegram bot application.

    Args:
        on_investigate: Async callback that takes a query string and runs an investigation.
                        Signature: async def handler(query: str) -> None
    """
    if not settings.telegram_configured:
        raise ValueError(
            "Telegram not configured. Set SHERLOCK_TELEGRAM_BOT_TOKEN and SHERLOCK_TELEGRAM_CHAT_ID."
        )

    app = Application.builder().token(settings.telegram_bot_token).build()

    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "🔍 *Sherlock Holmes AI*\n\n"
            "Send me any research question and I'll investigate it.\n\n"
            "Examples:\n"
            '• _"Who are the major players in the AI agent market?"_\n'
            '• _"What happened with the latest EU AI Act enforcement?"_\n'
            '• _"Compare React vs Svelte vs Solid for 2026 projects"_\n\n'
            "Commands:\n"
            "/status — Check if Sherlock is running\n"
            "/help — Show this message",
            parse_mode="Markdown",
        )

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await start_handler(update, context)

    async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("✅ Sherlock is online and ready to investigate.")

    async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages as investigation queries."""
        query = update.message.text.strip()
        if not query:
            return

        chat_id = str(update.effective_chat.id)

        # Only respond to the configured chat
        if chat_id != settings.telegram_chat_id:
            await update.message.reply_text("⛔ Unauthorized. This bot is private.")
            return

        await update.message.reply_text(
            f"🔍 *Starting investigation...*\n\n_{query}_",
            parse_mode="Markdown",
        )

        if on_investigate:
            # Run investigation in the background so the bot stays responsive
            asyncio.create_task(_safe_investigate(on_investigate, query))
        else:
            await update.message.reply_text(
                "⚠️ Investigation handler not configured. "
                "Run `sherlock telegram` to enable full functionality."
            )

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    return app


async def _safe_investigate(on_investigate: callable, query: str) -> None:
    """Run an investigation with error handling for the Telegram context."""
    try:
        await on_investigate(query)
    except Exception as e:
        logger.error(f"Investigation failed via Telegram: {e}")
        await send_notification(
            f"❌ *Investigation failed*\n\n_{query}_\n\nError: `{str(e)[:300]}`"
        )
