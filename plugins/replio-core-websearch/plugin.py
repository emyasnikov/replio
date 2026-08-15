import re
from html.parser import HTMLParser

import search
import display


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip_depth = 0
        self._skip_tags = frozenset({'script', 'style', 'svg', 'noscript'})
        self._block_tags = frozenset({
            'p', 'br', 'li', 'div', 'tr', 'td', 'th',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'blockquote', 'pre', 'hr',
        })

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip_depth += 1
        if self._skip_depth == 0 and tag in self._block_tags:
            self._parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip_depth = max(0, self._skip_depth - 1)
        if self._skip_depth == 0 and tag in self._block_tags:
            self._parts.append('\n')

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self):
        text = ''.join(self._parts)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n ', '\n', text)
        text = re.sub(r' \n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class _SearchService:
    def search(self, query: str, num: int = 5) -> list[dict]:
        return search.search(query, num)

    def display(self, query: str, results: list[dict]) -> str:
        return display.format_results(query, results)

    def context(self, query: str, results: list[dict]) -> str:
        return display.format_context(query, results)


SERVICE = _SearchService()


def register_services(services):
    services['search'] = SERVICE


def register_tools(registry):
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
        refine=True,
        category='search',
        permission='web',
        key_arg='query',
        short='Search the web',
    )
    def web_search(query: str) -> str:
        results = SERVICE.search(query)
        if not results:
            return 'No search results found.'
        return SERVICE.context(query, results)

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
        category='read',
        permission='read',
        key_arg='url',
        short="Fetch and read a web page's content",
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
            extractor = _TextExtractor()
            extractor.feed(content)
            text = extractor.text()
            if len(text) > 8000:
                text = text[:8000] + '\n... (truncated)'
            return text
        except Exception as e:
            return f'Error fetching page: {e}'
