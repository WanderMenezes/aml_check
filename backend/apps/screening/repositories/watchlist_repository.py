from django.db.models import Q
import re
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache
from django.conf import settings

from apps.intelligence.models import Country, CountryRiskEntry, WatchlistEntry
from common.utils.countries import canonical_country

from common.utils.strings import normalize_text
from apps.intelligence.models import SanctionsSource
from common.utils.fuzzy import similarity_score


class WatchlistRepository:
    @staticmethod
    def candidate_entries(name: str):
        normalized_name = normalize_text(name)
        if not normalized_name:
            return WatchlistEntry.objects.none()
        tokens = [token for token in normalized_name.split(" ") if token]
        query = Q(normalized_name__icontains=normalized_name)
        for token in tokens[:4]:
            query |= Q(normalized_name__icontains=token)
        return WatchlistEntry.objects.filter(is_active=True).filter(query).select_related("source").distinct()

    @staticmethod
    def country_risks(country: str):
        canonical = canonical_country(country) or country
        return CountryRiskEntry.objects.filter(is_active=True, country_name__iexact=canonical).select_related("source")

    @staticmethod
    def country_profile(country: str):
        canonical = canonical_country(country) or country
        return Country.objects.filter(normalized_name=normalize_text(canonical)).first()


    @staticmethod
    def external_site_matches(name: str, timeout: int = 5) -> list[dict]:
        """Search enabled `SanctionsSource` landing URLs/endpoints for occurrences of `name`.

        Returns a list of dicts with keys: source (SanctionsSource), url, title, snippet, score.
        """
        normalized_name = normalize_text(name)
        if not normalized_name:
            return []

        sources = list(SanctionsSource.objects.filter(enabled=True).exclude(landing_url="").all())

        # cache key per normalized name
        cache_ttl = settings.SCREENING_SETTINGS.get("EXTERNAL_CACHE_TTL", 300)
        cache_key = f"external_matches:{normalized_name}"
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached:
            return cached

        results: list[dict] = []

        # prefer aiohttp for async concurrent fetching
        try:
            import aiohttp
            AIOHTTP_AVAILABLE = True
        except Exception:
            aiohttp = None
            AIOHTTP_AVAILABLE = False

        async def fetch_aio(session, src, url):
            try:
                async with session.get(url, timeout=timeout) as resp:
                    if resp.status != 200:
                        return None
                    text = await resp.text()
            except Exception:
                return None
            return (src, url, text)

        def process_text(src, url, text):
            # extract title if present
            m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
            title = m.group(1).strip() if m else ""
            stripped = re.sub(r"<[^>]+>", " ", text)
            stripped = re.sub(r"\s+", " ", stripped).strip()
            normalized_page = normalize_text(stripped)
            if normalized_name in normalized_page:
                score = 100
                idx = normalized_page.find(normalized_name)
                start = max(0, idx - 60)
                end = min(len(normalized_page), idx + len(normalized_name) + 60)
                snippet = stripped[start:end]
            else:
                target = title or (stripped[:200] if stripped else "")
                score = similarity_score(name, target)
                snippet = (title or target)[:200]
            return {"source": src, "url": url, "title": title, "snippet": snippet, "score": int(score)}

        start_time = time.time()

        if AIOHTTP_AVAILABLE:
            concurrency = settings.SCREENING_SETTINGS.get("EXTERNAL_CONCURRENCY", 6)
            async def run_all():
                connector = aiohttp.TCPConnector(ssl=False)
                timeout_obj = aiohttp.ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj, headers={"User-Agent": "AMLCheck/1.0"}) as session:
                    tasks = []
                    for src in sources:
                        url = src.landing_url or src.endpoint
                        if not url:
                            continue
                        tasks.append(fetch_aio(session, src, url))
                    if not tasks:
                        return []
                    results_raw = await asyncio.gather(*tasks, return_exceptions=True)
                    out = []
                    for item in results_raw:
                        if not item or isinstance(item, Exception):
                            continue
                        src, url, text = item
                        out.append(process_text(src, url, text))
                    return out

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(run_all())
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        else:
            # fallback: use ThreadPoolExecutor with requests
            def fetch_req(src):
                try:
                    import requests
                    from requests.exceptions import RequestException
                except ImportError:
                    return None
                url = src.landing_url or src.endpoint
                if not url:
                    return None
                try:
                    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "AMLCheck/1.0"})
                    if resp.status_code != 200 or not resp.text:
                        return None
                    return (src, url, resp.text)
                except Exception:
                    return None

            with ThreadPoolExecutor(max_workers=settings.SCREENING_SETTINGS.get("EXTERNAL_CONCURRENCY", 6)) as ex:
                futures = [ex.submit(fetch_req, src) for src in sources]
                for fut in futures:
                    item = None
                    try:
                        item = fut.result(timeout=timeout + 1)
                    except Exception:
                        continue
                    if not item:
                        continue
                    src, url, text = item
                    results.append(process_text(src, url, text))

        # sort and cache
        results = sorted(results, key=lambda r: r["score"], reverse=True)
        try:
            cache.set(cache_key, results, cache_ttl)
        except Exception:
            pass
        return results
