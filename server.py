import xml.etree.ElementTree as ET
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="PubMed Notion Search")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

@app.get("/api/translate")
def translate(q: str = Query(..., description="翻訳するテキスト")):
    """日本語テキストを英語に翻訳する（MyMemory無料API使用）。"""
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": q, "langpair": "ja|en"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("responseStatus") == 200:
            return {"translated": data["responseData"]["translatedText"], "original": q}
        raise HTTPException(status_code=502, detail=f"翻訳サービスエラー: {data.get('responseDetails', '')}")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"翻訳リクエスト失敗: {e}")


# ---------------------------------------------------------------------------
# PubMed
# ---------------------------------------------------------------------------

@app.get("/api/search")
def search_pubmed(q: str = Query(..., description="検索キーワード"), max_results: int = 20):
    try:
        search_resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": q, "retmax": max_results, "retmode": "json", "sort": "relevance"},
            timeout=15,
        )
        search_resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"PubMed search error: {e}")

    ids = search_resp.json()["esearchresult"]["idlist"]
    if not ids:
        return {"articles": [], "total": 0}

    try:
        fetch_resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "xml"},
            timeout=30,
        )
        fetch_resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"PubMed fetch error: {e}")

    articles = _parse_xml(fetch_resp.text)
    return {"articles": articles, "total": len(articles)}


def _parse_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    articles = []
    for article in root.findall(".//PubmedArticle"):
        pmid = getattr(article.find(".//PMID"), "text", "")

        title_elem = article.find(".//ArticleTitle")
        title = "".join(title_elem.itertext()).strip() if title_elem is not None else "(タイトルなし)"

        abstract_parts = []
        for a in article.findall(".//AbstractText"):
            label = a.get("Label")
            text = "".join(a.itertext()).strip()
            abstract_parts.append(f"[{label}] {text}" if label else text)
        abstract = " ".join(abstract_parts) if abstract_parts else "(アブストラクトなし)"

        authors = []
        for author in article.findall(".//Author"):
            last = author.findtext("LastName", "")
            fore = author.findtext("ForeName", "")
            if last:
                authors.append(f"{last} {fore}".strip())
        authors_str = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")

        journal = article.findtext(".//Journal/Title") or article.findtext(".//MedlineTA") or ""
        year_elem = article.find(".//PubDate/Year") or article.find(".//PubDate/MedlineDate")
        year = year_elem.text[:4] if year_elem is not None else ""

        articles.append({
            "pmid": pmid,
            "title": title,
            "authors": authors_str,
            "journal": journal,
            "year": year,
            "abstract": abstract,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return articles


# ---------------------------------------------------------------------------
# Notion
# ---------------------------------------------------------------------------

class TestNotionRequest(BaseModel):
    notion_token: str
    parent_page_id: str


class CreateDbRequest(BaseModel):
    notion_token: str
    parent_page_id: str
    name: str = "PubMed文献リスト"


class SaveRequest(BaseModel):
    notion_token: str
    database_id: str
    articles: list[dict]
    query: str


def _notion_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def _clean_page_id(raw: str) -> str:
    """URLまたはIDからNotionページIDを抽出してUUID形式で返す。"""
    import re
    raw = raw.strip()
    # UUID形式（ハイフンあり）がそのまま渡された場合
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    if uuid_pattern.match(raw):
        return raw.lower()
    # URLから32文字の16進数IDを探す
    hex32 = re.findall(r'([0-9a-f]{32})', raw.lower().replace('-', ''))
    if hex32:
        r = hex32[-1]  # 末尾のIDを優先
        return f"{r[:8]}-{r[8:12]}-{r[12:16]}-{r[16:20]}-{r[20:]}"
    # ハイフンなし32文字
    cleaned = raw.replace("-", "").replace(" ", "")
    if len(cleaned) == 32 and all(c in '0123456789abcdefABCDEF' for c in cleaned):
        r = cleaned.lower()
        return f"{r[:8]}-{r[8:12]}-{r[12:16]}-{r[16:20]}-{r[20:]}"
    return raw


@app.post("/api/test-notion")
def test_notion(req: TestNotionRequest):
    """APIトークンとページIDの疎通確認を行う。"""
    headers = _notion_headers(req.notion_token)

    # ① トークン確認
    r = requests.get("https://api.notion.com/v1/users/me", headers=headers, timeout=10)
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="APIトークンが無効です。secret_ から始まる正しいトークンか確認してください。")
    if not r.ok:
        raise HTTPException(status_code=r.status_code, detail=f"トークン確認エラー: {r.text}")

    # ② ページ確認
    page_id = _clean_page_id(req.parent_page_id)
    r2 = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, timeout=10)
    if r2.status_code == 404:
        raise HTTPException(status_code=404,
            detail="ページが見つかりません。①ページIDが正しいか、②インテグレーションをページに「接続」しているか確認してください。")
    if not r2.ok:
        raise HTTPException(status_code=r2.status_code, detail=f"ページ確認エラー: {r2.text}")

    return {"ok": True, "page_id": page_id, "message": "接続成功！APIトークンとページIDは正しく設定されています。"}


@app.post("/api/create-database")
def create_database(req: CreateDbRequest):
    parent_id = _clean_page_id(req.parent_page_id)
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "title": [{"type": "text", "text": {"content": req.name[:100]}}],
        "properties": {
            "Title": {"title": {}},
            "PMID": {"rich_text": {}},
            "Authors": {"rich_text": {}},
            "Journal": {"rich_text": {}},
            "Year": {"number": {}},
            "Search Query": {"rich_text": {}},
            "URL": {"url": {}},
        },
    }
    try:
        resp = requests.post(
            "https://api.notion.com/v1/databases",
            headers=_notion_headers(req.notion_token),
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    return {"database_id": resp.json()["id"]}


@app.post("/api/save")
def save_articles(req: SaveRequest):
    saved, errors = [], []
    for art in req.articles:
        year_val = int(art["year"]) if art.get("year", "").isdigit() else None
        payload = {
            "parent": {"database_id": req.database_id},
            "properties": {
                "Title": {"title": [{"text": {"content": art["title"][:255]}}]},
                "PMID": {"rich_text": [{"text": {"content": art["pmid"]}}]},
                "Authors": {"rich_text": [{"text": {"content": art["authors"][:1999]}}]},
                "Journal": {"rich_text": [{"text": {"content": art["journal"][:1999]}}]},
                "Year": {"number": year_val},
                "Search Query": {"rich_text": [{"text": {"content": req.query[:1999]}}]},
                "URL": {"url": art["url"]},
            },
            "children": [
                {"object": "block", "type": "heading_2",
                 "heading_2": {"rich_text": [{"text": {"content": "Abstract"}}]}},
                {"object": "block", "type": "paragraph",
                 "paragraph": {"rich_text": [{"text": {"content": art["abstract"][:1999]}}]}},
            ],
        }
        try:
            resp = requests.post(
                "https://api.notion.com/v1/pages",
                headers=_notion_headers(req.notion_token),
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            saved.append(art["pmid"])
        except requests.HTTPError as e:
            errors.append({"pmid": art["pmid"], "error": e.response.text})

    return {"saved": saved, "errors": errors}
