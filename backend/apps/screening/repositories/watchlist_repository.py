import re
import hashlib
import html
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from django.core.cache import cache
from django.conf import settings
from django.db.models import Q

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
    def external_site_matches(name: str, timeout: int = 5, include_all: bool = False) -> list[dict]:
        """Search every URL registered in enabled `SanctionsSource` records.

        Returns matched sources by default. With include_all=True, returns every
        enabled source checked, including NO_MATCH and ERROR statuses.
        """
        normalized_name = normalize_text(name)
        if not normalized_name:
            return []

        sources = list(
            SanctionsSource.objects.filter(enabled=True)
            .exclude(Q(landing_url="") & Q(endpoint=""))
            .order_by("code")
        )

        cache_ttl = settings.SCREENING_SETTINGS.get("EXTERNAL_CACHE_TTL", 300)
        min_score = int(settings.SCREENING_SETTINGS.get("MIN_EXTERNAL_SCORE", settings.SCREENING_SETTINGS["MIN_FUZZY_SCORE"]))
        max_bytes = int(settings.SCREENING_SETTINGS.get("EXTERNAL_MAX_BYTES", 750_000))
        source_signature = ":".join(
            f"{src.pk}-{src.updated_at.timestamp():.0f}-{src.landing_url}-{src.endpoint}" for src in sources
        )
        cache_seed = f"{normalized_name}:{int(include_all)}:{min_score}:{source_signature}"
        cache_key = f"external_matches:v5:{hashlib.sha1(cache_seed.encode('utf-8')).hexdigest()}"
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached is not None:
            return cached

        def render_search_url(url: str) -> str:
            encoded_query = urlencode({"q": name}).split("=", 1)[1]
            return (
                url.replace("{query}", encoded_query)
                .replace("{name}", encoded_query)
                .replace("%7Bquery%7D", encoded_query)
                .replace("%7Bname%7D", encoded_query)
            )

        def wordpress_search_url(url: str) -> str:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ""
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            query["s"] = name
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", urlencode(query), ""))

        def source_urls(src) -> list[str]:
            urls = []
            for value, allow_site_search in ((src.landing_url, True), (src.endpoint, False)):
                if not value:
                    continue
                rendered = render_search_url(value)
                if rendered not in urls:
                    urls.append(rendered)
                if allow_site_search and "{query}" not in value and "{name}" not in value and src.source_format == SanctionsSource.SourceFormat.HTML:
                    search_url = wordpress_search_url(value)
                    if search_url and search_url not in urls:
                        urls.append(search_url)
            return urls

        important_keywords = {
            "corrupcao",
            "corrupção",
            "fraude",
            "crime",
            "criminal",
            "acusado",
            "acusada",
            "investigacao",
            "investigação",
            "tribunal",
            "ministerio publico",
            "ministério público",
            "policia",
            "polícia",
            "processo",
            "condenado",
            "condenada",
            "sancao",
            "sanção",
            "governo",
            "contrato",
            "divida",
            "dívida",
            "banco",
            "empresa",
            "fundos",
            "branqueamento",
            "lavagem",
            "money laundering",
            "sanction",
            "fraud",
            "court",
            "investigation",
            "corruption",
        }

        def important_terms(value: str) -> list[str]:
            normalized = normalize_text(value)
            found = []
            for keyword in important_keywords:
                if normalize_text(keyword) in normalized:
                    found.append(keyword)
            return sorted(set(found))[:6]

        def classify(score: int, matched: bool, status: str, terms: list[str] | None = None) -> tuple[str, str, str]:
            if status.startswith("ERROR") or status.startswith("HTTP_"):
                return ("unavailable", "Fonte indisponivel; confirmar manualmente se for critica.", "Baixo")
            if not matched:
                return ("clear", "Sem indicio relevante nesta fonte.", "Baixo")
            if terms:
                return ("probable_match", f"Resultado encontrado com termos relevantes para due diligence: {', '.join(terms)}.", "Alto")
            if score >= 98:
                return ("probable_match", "Nome encontrado diretamente na fonte registada.", "Alto")
            if score >= 90:
                return ("possible_match", "Similaridade alta; requer validacao documental.", "Medio")
            return ("weak_signal", "Sinal fraco; usar apenas como contexto auxiliar.", "Baixo")

        def source_payload(src, url: str, status: str, *, title: str = "", snippet: str = "", score: int = 0, matched: bool = False, evidence_url: str = "", terms: list[str] | None = None):
            terms = terms or important_terms(f"{title} {snippet}")
            decision, decision_reason, evidence_level = classify(int(score), matched, status, terms)
            return {
                "source": src,
                "url": evidence_url or url,
                "checked_url": url,
                "title": title,
                "snippet": snippet,
                "score": int(score),
                "status": status,
                "matched": matched,
                "decision": decision,
                "decision_reason": decision_reason,
                "evidence_level": evidence_level,
                "important_terms": terms,
                "source_name": src.name if src else "External source",
                "source_code": src.code if src else "EXTERNAL",
            }

        def process_text(src, url, text):
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)
            m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
            title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""

            def strip_tags(value: str) -> str:
                return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip())

            def score_candidate(candidate: dict) -> dict:
                content = f"{candidate.get('title', '')} {candidate.get('snippet', '')}".strip()
                normalized_content = normalize_text(content)
                exact = normalized_name in normalized_content
                if exact:
                    score = 100
                else:
                    score = max(
                        similarity_score(name, candidate.get("title", "")),
                        similarity_score(name, candidate.get("snippet", "")[:300]),
                    )
                candidate["score"] = score
                candidate["matched"] = exact or score >= min_score
                candidate["terms"] = important_terms(content)
                return candidate

            candidates: list[dict] = []
            for block_match in re.finditer(r"<article\b[^>]*>(.*?)</article>", text, re.IGNORECASE | re.DOTALL):
                block = block_match.group(1)
                link_match = re.search(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", block, re.IGNORECASE | re.DOTALL)
                heading_match = re.search(r"<h[1-4]\b[^>]*>(.*?)</h[1-4]>", block, re.IGNORECASE | re.DOTALL)
                block_text = strip_tags(block)
                candidates.append(
                    {
                        "title": strip_tags(heading_match.group(1) if heading_match else link_match.group(2) if link_match else block_text[:180]),
                        "snippet": block_text[:700],
                        "url": urljoin(url, link_match.group(1)) if link_match else url,
                    }
                )

            for link_match in re.finditer(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.IGNORECASE | re.DOTALL):
                link_text = strip_tags(link_match.group(2))
                if len(link_text) < 4:
                    continue
                normalized_link = normalize_text(link_text)
                if normalized_name in normalized_link or any(token in normalized_link for token in normalized_name.split() if len(token) > 2):
                    candidates.append({"title": link_text[:220], "snippet": link_text[:500], "url": urljoin(url, link_match.group(1))})

            scored = [score_candidate(candidate) for candidate in candidates]
            scored_matches = [candidate for candidate in scored if candidate["matched"]]
            if scored_matches:
                best = sorted(scored_matches, key=lambda item: (bool(item["terms"]), item["score"], len(item["snippet"])), reverse=True)[0]
                return source_payload(
                    src,
                    url,
                    "FOUND",
                    title=best["title"],
                    snippet=best["snippet"][:500],
                    score=best["score"],
                    matched=True,
                    evidence_url=best["url"],
                    terms=best["terms"],
                )

            stripped = strip_tags(text)
            normalized_page = normalize_text(stripped)
            search_result_title = normalize_text(title).startswith(("resultados da pesquisa", "search results"))
            if normalized_name in normalized_page and not search_result_title:
                score = 100
                first_token = next((token for token in name.split() if len(token) > 2), name)
                token_match = re.search(re.escape(first_token), stripped, re.IGNORECASE)
                idx = token_match.start() if token_match else max(0, stripped.lower().find(name.lower()))
                start = max(0, idx - 60)
                end = min(len(stripped), idx + len(name) + 120)
                snippet = stripped[start:end]
                matched = True
            else:
                text_candidates = [title if not search_result_title else "", stripped[:300]]
                score = max((similarity_score(name, candidate) for candidate in text_candidates if candidate), default=0)
                snippet = (title if not search_result_title else stripped[:300])[:300]
                matched = score >= min_score
            return source_payload(src, url, "FOUND" if matched else "NO_MATCH", title=title, snippet=snippet, score=score, matched=matched)

        def fetch_req(src, url):
            if not url:
                return source_payload(src, "", "NO_URL")
            try:
                import requests
            except ImportError:
                return source_payload(src, url, "ERROR", snippet="Python requests package is not available.")
            try:
                resp = requests.get(
                    url,
                    timeout=(min(timeout, 3), timeout),
                    headers={"User-Agent": "AMLCheck/1.0 (+compliance screening)", "Accept": "text/html,application/xml,text/xml,text/plain,*/*"},
                    stream=True,
                )
            except Exception as exc:
                return source_payload(src, url, "ERROR", snippet=str(exc)[:200])
            if resp.status_code != 200:
                return source_payload(src, url, f"HTTP_{resp.status_code}", snippet=(resp.reason or "")[:200])
            chunks = []
            total = 0
            try:
                for chunk in resp.iter_content(chunk_size=65536, decode_unicode=True):
                    if not chunk:
                        continue
                    chunks.append(chunk if isinstance(chunk, str) else chunk.decode(resp.encoding or "utf-8", errors="ignore"))
                    total += len(chunks[-1])
                    if total >= max_bytes:
                        break
            except Exception as exc:
                return source_payload(src, url, "ERROR", snippet=str(exc)[:200])
            text = "".join(chunks)
            if not text:
                return source_payload(src, url, "EMPTY")
            return process_text(src, url, text)

        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=settings.SCREENING_SETTINGS.get("EXTERNAL_CONCURRENCY", 6)) as ex:
            futures = [ex.submit(fetch_req, src, url) for src in sources for url in source_urls(src)]
            for fut in futures:
                try:
                    results.append(fut.result(timeout=timeout + 1))
                except Exception:
                    continue

        best_by_url: dict[str, dict] = {}
        for result in results:
            parsed = urlparse(result.get("url") or "")
            key = result.get("url") or f"{result.get('source_code')}:{parsed.netloc}"
            existing = best_by_url.get(key)
            if existing is None or (result.get("matched"), result.get("score", 0)) > (existing.get("matched"), existing.get("score", 0)):
                best_by_url[key] = result
        results = list(best_by_url.values())
        if not include_all:
            results = [result for result in results if result.get("matched")]
        results = sorted(results, key=lambda r: (bool(r.get("matched")), r["score"], r.get("source_name", "")), reverse=True)
        try:
            cache.set(cache_key, results, cache_ttl)
        except Exception:
            pass
        return results
