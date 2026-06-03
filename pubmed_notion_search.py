import streamlit as st
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="PubMed → Notion 文献検索", layout="wide")
st.title("PubMed 文献検索 → Notion 保存")
st.caption("キーワードでPubMedを検索し、文献のAbstractをNotionデータベースへ保存します。")

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("設定")
    notion_token = st.text_input(
        "Notion API トークン",
        type="password",
        help="Notionインテグレーションのシークレットトークンを入力してください",
    )
    parent_page_input = st.text_input(
        "Notion 親ページURL または ID",
        help="データベースを作成するNotionページのURLまたはIDを入力してください",
    )
    max_results = st.number_input("最大検索件数", min_value=1, max_value=100, value=20)
    st.divider()
    st.markdown(
        "**Notionトークンの取得方法**\n"
        "1. [Notion Integrations](https://www.notion.so/my-integrations) でインテグレーションを作成\n"
        "2. 保存先ページでインテグレーションに接続を許可\n"
        "3. シークレットトークンをここに貼り付け"
    )


def extract_page_id(raw: str) -> str:
    """NotionページURLまたはIDからpage IDを抽出する。"""
    raw = raw.strip()
    # URLの場合: https://www.notion.so/...?v=... or /page-title-{id}
    # IDはハイフンなし32文字または標準UUID形式
    if "notion.so" in raw:
        # パスの最後のセグメントからIDを取得
        path = raw.split("?")[0].rstrip("/")
        segment = path.split("/")[-1]
        # セグメント末尾のハイフン区切りUUID or 32文字ID
        raw_id = segment.split("-")[-1] if "-" in segment else segment
        if len(raw_id) == 32:
            return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"
        return raw_id
    # ハイフンなし32文字
    cleaned = raw.replace("-", "")
    if len(cleaned) == 32:
        return f"{cleaned[:8]}-{cleaned[8:12]}-{cleaned[12:16]}-{cleaned[16:20]}-{cleaned[20:]}"
    return raw


def search_pubmed(query: str, retmax: int) -> list[dict]:
    """PubMed E-utilities APIで文献を検索してメタデータとAbstractを返す。"""
    search_resp = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json", "sort": "relevance"},
        timeout=15,
    )
    search_resp.raise_for_status()
    ids = search_resp.json()["esearchresult"]["idlist"]
    if not ids:
        return []

    fetch_resp = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "xml"},
        timeout=30,
    )
    fetch_resp.raise_for_status()
    return _parse_pubmed_xml(fetch_resp.text)


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    articles = []
    for article in root.findall(".//PubmedArticle"):
        pmid = getattr(article.find(".//PMID"), "text", "")

        title_elem = article.find(".//ArticleTitle")
        title = "".join(title_elem.itertext()).strip() if title_elem is not None else "(タイトルなし)"

        abstract_elems = article.findall(".//AbstractText")
        abstract_parts = []
        for a in abstract_elems:
            label = a.get("Label")
            text = "".join(a.itertext()).strip()
            if label:
                abstract_parts.append(f"[{label}] {text}")
            else:
                abstract_parts.append(text)
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
        year = (year_elem.text[:4] if year_elem is not None else "")

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


def _notion_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def create_notion_database(token: str, parent_page_id: str) -> str:
    """Notionの親ページ配下にPubMed文献用データベースを作成してIDを返す。"""
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "PubMed文献リスト"}}],
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
    resp = requests.post(
        "https://api.notion.com/v1/databases",
        headers=_notion_headers(token),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def save_paper_to_notion(token: str, database_id: str, paper: dict, query: str) -> None:
    """1件の文献をNotionデータベースに保存する。"""
    year_val = int(paper["year"]) if paper["year"].isdigit() else None
    # Notionのrich_textは2000文字上限
    abstract = paper["abstract"][:1999]
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {"title": [{"text": {"content": paper["title"][:255]}}]},
            "PMID": {"rich_text": [{"text": {"content": paper["pmid"]}}]},
            "Authors": {"rich_text": [{"text": {"content": paper["authors"][:1999]}}]},
            "Journal": {"rich_text": [{"text": {"content": paper["journal"][:1999]}}]},
            "Year": {"number": year_val},
            "Search Query": {"rich_text": [{"text": {"content": query[:1999]}}]},
            "URL": {"url": paper["url"]},
        },
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Abstract"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": abstract}}]},
            },
        ],
    }
    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_notion_headers(token),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()


# --- Session state initialization ---
if "articles" not in st.session_state:
    st.session_state.articles = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "notion_db_id" not in st.session_state:
    st.session_state.notion_db_id = ""
if "saved_pmids" not in st.session_state:
    st.session_state.saved_pmids = set()

# --- Search UI ---
st.subheader("文献検索")
col_input, col_btn = st.columns([4, 1])
with col_input:
    query = st.text_input("検索キーワード", placeholder="例: Kawasaki disease IVIG resistance", label_visibility="collapsed")
with col_btn:
    search_clicked = st.button("検索", use_container_width=True, type="primary")

if search_clicked and query:
    with st.spinner("PubMedを検索中..."):
        try:
            st.session_state.articles = search_pubmed(query, int(max_results))
            st.session_state.last_query = query
            st.session_state.saved_pmids = set()
        except requests.HTTPError as e:
            st.error(f"PubMed APIエラー: {e}")
        except Exception as e:
            st.error(f"検索中にエラーが発生しました: {e}")

articles = st.session_state.articles
last_query = st.session_state.last_query

if not articles and last_query:
    st.info(f'"{last_query}" に一致する文献が見つかりませんでした。')

# --- Results ---
if articles:
    st.markdown(f"**{len(articles)}件** が見つかりました（検索語: `{last_query}`）")
    st.divider()

    selected_pmids = []
    for i, art in enumerate(articles):
        is_saved = art["pmid"] in st.session_state.saved_pmids
        label_suffix = " ✅ 保存済" if is_saved else ""

        with st.container():
            col_check, col_content = st.columns([0.05, 0.95])
            with col_check:
                checked = st.checkbox("", key=f"chk_{art['pmid']}", value=False, disabled=is_saved)
            with col_content:
                st.markdown(
                    f"**{i+1}. [{art['title']}]({art['url']}){label_suffix}**\n\n"
                    f"{art['authors']}  \n"
                    f"*{art['journal']}* {art['year']}"
                )
                with st.expander("Abstract を表示"):
                    st.write(art["abstract"])
            if checked and not is_saved:
                selected_pmids.append(art["pmid"])
        st.divider()

    # --- Save to Notion ---
    st.subheader("Notionへ保存")
    if not notion_token or not parent_page_input:
        st.warning("サイドバーに Notion APIトークン と 親ページID を入力してください。")
    else:
        if st.button(f"選択した {len(selected_pmids)} 件を Notion に保存", type="primary", disabled=len(selected_pmids) == 0):
            parent_id = extract_page_id(parent_page_input)
            progress = st.progress(0)
            status = st.empty()

            # データベースIDがなければ作成
            if not st.session_state.notion_db_id:
                status.info("Notionにデータベースを作成中...")
                try:
                    st.session_state.notion_db_id = create_notion_database(notion_token, parent_id)
                    status.success(f"データベースを作成しました（ID: `{st.session_state.notion_db_id}`）")
                except requests.HTTPError as e:
                    status.error(f"データベース作成エラー: {e.response.text}")
                    st.stop()

            db_id = st.session_state.notion_db_id
            selected_articles = [a for a in articles if a["pmid"] in selected_pmids]
            errors = []
            for idx, art in enumerate(selected_articles):
                status.info(f"保存中 ({idx + 1}/{len(selected_articles)}): {art['title'][:60]}...")
                try:
                    save_paper_to_notion(notion_token, db_id, art, last_query)
                    st.session_state.saved_pmids.add(art["pmid"])
                except requests.HTTPError as e:
                    errors.append(f"PMID {art['pmid']}: {e.response.text}")
                progress.progress((idx + 1) / len(selected_articles))

            if errors:
                status.error("一部の保存に失敗しました:\n" + "\n".join(errors))
            else:
                status.success(f"{len(selected_articles)} 件を Notion データベースに保存しました！")
            st.rerun()
