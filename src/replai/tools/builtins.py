import json


def register_tools(registry):
    from ..web.search import search as web_search_fn
    from ..web.display import format_context

    @registry.register(
        name='web_search',
        description='Search the web for current information. Use this to find recent news, facts, documentation, and any information that may be time-sensitive or outside the model\'s training data.',
        parameters={
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The search query — be specific and concise',
                },
            },
            'required': ['query'],
        },
    )
    def web_search(query: str) -> str:
        results = web_search_fn(query)
        if not results:
            return 'No search results found.'
        return format_context(query, results)

    @registry.register(
        name='fetch_page',
        description='Fetch and read the full content of a web page. Use this when search result snippets are insufficient and you need detailed information from a specific URL.',
        parameters={
            'type': 'object',
            'properties': {
                'url': {
                    'type': 'string',
                    'description': 'The full URL of the page to fetch',
                },
            },
            'required': ['url'],
        },
    )
    def fetch_page(url: str) -> str:
        import urllib.request
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode('utf-8', errors='replace')
            import re
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 8000:
                text = text[:8000] + '\n... (truncated)'
            return text
        except Exception as e:
            return f'Error fetching page: {e}'
