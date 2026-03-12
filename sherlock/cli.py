"""Sherlock Holmes AI — CLI entrypoint."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="sherlock",
    help="🔍 AI-powered research and investigation agent",
    add_completion=False,
)
console = Console()


@app.command()
def investigate(
    query: str = typer.Argument(..., help="The research question or investigation brief"),
    output: str = typer.Option("sherlock/outputs", "--output", "-o", help="Output directory"),
    model: str = typer.Option("", "--model", "-m", help="Override LLM model"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    notify: bool = typer.Option(False, "--notify", "-n", help="Send Telegram notifications"),
) -> None:
    """Run a full investigation on a query."""
    console.print(
        Panel(
            f"[bold]🔍 Investigation:[/bold] {query}",
            title="Sherlock Holmes AI",
            border_style="blue",
        )
    )

    asyncio.run(_run_investigation(query, output, model, verbose, notify))


async def _run_investigation(
    query: str, output_dir: str, model: str, verbose: bool, notify: bool
) -> None:
    from sherlock.agents.conductor import execute_investigation, plan_investigation
    from sherlock.agents.reporter import generate_report, save_report
    from sherlock.config import settings

    if model:
        settings.model = model
    settings.output_dir = Path(output_dir)

    # Enable Telegram if --notify and credentials exist
    should_notify = notify and settings.telegram_configured

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Phase 1: Plan
        task = progress.add_task("Planning investigation...", total=None)
        investigation = await plan_investigation(query)
        progress.update(task, description=f"Planned {len(investigation.sub_tasks)} sub-tasks")

        if verbose:
            for st in investigation.sub_tasks:
                console.print(f"  → [dim]{st.agent}:[/dim] {st.description}")

        # Phase 2: Execute
        progress.update(task, description="Executing research...")
        investigation = await execute_investigation(investigation, notify=should_notify)

        completed = len([t for t in investigation.sub_tasks if t.status == "completed"])
        progress.update(
            task,
            description=f"Completed {completed}/{len(investigation.sub_tasks)} tasks, {len(investigation.findings)} findings",
        )

        # Phase 3: Report
        progress.update(task, description="Generating report...")
        markdown = await generate_report(investigation)
        report_path = await save_report(investigation, markdown)
        investigation.report_path = str(report_path)

        # Phase 4: Telegram delivery
        if should_notify:
            from sherlock.tools.telegram import notify_investigation_complete

            progress.update(task, description="Sending Telegram notification...")
            await notify_investigation_complete(query, len(investigation.findings), report_path)

        progress.update(task, description="Done!")

    console.print(f"\n✅ Report saved to [bold green]{report_path}[/bold green]")
    console.print(f"📊 Findings: {len(investigation.findings)}")
    console.print(f"📝 Sub-tasks: {completed}/{len(investigation.sub_tasks)} completed")
    if should_notify:
        console.print("📱 Telegram notification sent")


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
) -> None:
    """Start the Sherlock API server with the report viewer."""
    import uvicorn

    console.print(
        Panel(
            f"Starting Sherlock API at [bold]http://{host}:{port}[/bold]",
            title="Sherlock Holmes AI — Server",
            border_style="green",
        )
    )
    uvicorn.run("sherlock.api:app", host=host, port=port, reload=True)


@app.command()
def telegram() -> None:
    """Start the Telegram bot — receive investigation requests via message."""
    from sherlock.config import settings
    from sherlock.tools.telegram import create_bot_application

    if not settings.telegram_configured:
        console.print(
            "[red]Telegram not configured.[/red]\n"
            "Set SHERLOCK_TELEGRAM_BOT_TOKEN and SHERLOCK_TELEGRAM_CHAT_ID in .env"
        )
        raise typer.Exit(1)

    async def handle_telegram_investigation(query: str) -> None:
        """Callback for the bot: runs a full investigation with notifications."""
        from sherlock.agents.conductor import execute_investigation, plan_investigation
        from sherlock.agents.reporter import generate_report, save_report
        from sherlock.tools.telegram import notify_investigation_complete

        investigation = await plan_investigation(query)
        investigation = await execute_investigation(investigation, notify=True)
        markdown = await generate_report(investigation)
        report_path = await save_report(investigation, markdown)
        await notify_investigation_complete(query, len(investigation.findings), report_path)

    console.print(
        Panel(
            "Listening for messages...\nSend a research question to your bot on Telegram.",
            title="🤖 Sherlock Telegram Bot",
            border_style="green",
        )
    )

    bot_app = create_bot_application(on_investigate=handle_telegram_investigation)
    bot_app.run_polling()


@app.command()
def reports() -> None:
    """List all generated investigation reports."""
    from sherlock.config import settings

    output_dir = settings.output_dir
    if not output_dir.exists():
        console.print("[dim]No reports found.[/dim]")
        return

    md_files = sorted(output_dir.glob("*.md"), reverse=True)
    if not md_files:
        console.print("[dim]No reports found.[/dim]")
        return

    console.print(f"\n[bold]📁 Reports ({len(md_files)}):[/bold]\n")
    for f in md_files:
        size_kb = f.stat().st_size / 1024
        console.print(f"  {f.name}  [dim]({size_kb:.1f} KB)[/dim]")


if __name__ == "__main__":
    app()
