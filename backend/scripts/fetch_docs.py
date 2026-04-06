import os
import asyncio
from typing import List
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Инициализация консоли для красивого вывода
console = Console()

# Загрузка переменных окружения из .env (путь к backend/.env)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

async def crawl_and_save(base_url: str, include_paths: List[str], filename: str):
    if not FIRECRAWL_API_KEY:
        console.print("[bold red]Ошибка:[/bold red] FIRECRAWL_API_KEY не найден в .env")
        return

    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    console.print(f"\n[bold blue]Начинаю сбор документации:[/bold blue] {base_url}")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description=f"Краулинг {base_url}...", total=None)
            loop = asyncio.get_event_loop()
            
            # Используем v1 API — он более стабилен для фильтрации по include_paths в текущей SDK
            def run_crawl():
                return app.v1.crawl_url(
                    url=base_url,
                    include_paths=include_paths,
                    limit=30
                )
            result_obj = await loop.run_in_executor(None, run_crawl)

        # Результат v1 — V1CrawlStatusResponse
        data = getattr(result_obj, 'data', [])
        status = getattr(result_obj, 'status', 'unknown')

        if status == "completed" and data:
            full_markdown = []
            for doc in data:
                # doc — это V1FirecrawlDocument
                url = getattr(doc, 'url', None) or "Unknown URL"
                markdown = getattr(doc, 'markdown', None) or ""
                
                # Поиск URL в метаданных если url пуст
                if not url or url == "Unknown URL":
                    meta = getattr(doc, 'metadata', {})
                    if isinstance(meta, dict):
                        url = meta.get('sourceURL') or meta.get('url') or url
                    elif hasattr(meta, 'sourceURL'):
                        url = getattr(meta, 'sourceURL')

                if markdown:
                    full_markdown.append(f"# {url}\n\n{markdown}\n\n---\n")
                    console.print(f" [green]✔[/green] {url}")

            if not full_markdown:
                console.print(f"[yellow]Предупреждение:[/yellow] Markdown контент не найден.")
                return

            output_path = os.path.join(os.path.dirname(__file__), '..', '..', filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(full_markdown))
            console.print(f"[bold green]Успешно сохранено:[/bold green] {filename} ({len(full_markdown)} страниц)")
        else:
            err = getattr(result_obj, 'error', f"Статус: {status}")
            console.print(f"[bold red]Ошибка:[/bold red] {err}")

    except Exception as e:
        console.print(f"[bold red]Критическая ошибка:[/bold red] {str(e)}")

async def main():
    # Prodamus
    await crawl_and_save(
        "https://help.prodamus.ru",
        [
            "payform/integracii/rest-api/*",
            "payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/*",
            "payform/uvedomleniya/*"
        ],
        "Docs/integrations/PRODAMUS_API.md"
    )

    # Kinescope
    await crawl_and_save(
        "https://docs.kinescope.ru",
        [
            "instrukcii-dlya-razrabotchikov/*",
            "zashita-kontenta/*",
            "videopleer-nastrojka-i-vstraivanie/*"
        ],
        "Docs/integrations/KINESCOPE_API.md"
    )

if __name__ == "__main__":
    asyncio.run(main())
