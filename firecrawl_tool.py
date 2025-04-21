from smolagents import Tool
import os
from dotenv import load_dotenv

class FirecrawlCrawlTool(Tool):
    name = "firecrawl_crawl"
    description = """
    This tool crawls up to eight pages of a given website using the Firecrawl API and returns the markdown content of each crawled page as a list.
    """
    inputs = {
        "url": {
            "type": "string",
            "description": "The website URL to crawl."
        }
    }
    output_type = "array"

    def forward(self, url: str) -> list:
        load_dotenv()
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY not found.")

        from firecrawl import FirecrawlApp

        app = FirecrawlApp(api_key=api_key)
        crawl_status = app.crawl_url(
            url,
            params={
                'limit': 8,
                'scrapeOptions': {'formats': ['markdown']}
            },
            poll_interval=30
        )
        data = crawl_status.get('data', [])
        return [item['markdown'] for item in data if 'markdown' in item]

firecrawl_crawl_tool = FirecrawlCrawlTool()