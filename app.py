"""Streamlit arayüzü: yerel RAG asistanını tarayıcıda kullanır."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from local_rag.foundry_chat import DEFAULT_MODEL  # noqa: E402
from local_rag.rag import answer_from_knowledge_base  # noqa: E402
from local_rag.store import connect, count_chunks  # noqa: E402


DB_PATH = ROOT / "data" / "knowledge.db"
EXAMPLE_QUESTIONS = (
    "Projenin 4. hafta hedefi nedir?",
    "RAG sisteminde SQLite neden kullanılıyor?",
    "Son hafta hangi teslimler yapılacak?",
)


def knowledge_base_status() -> tuple[bool, int]:
    """Bilgi bankasının kullanıma hazır olup olmadığını döndürür."""
    if not DB_PATH.exists():
        return False, 0
    with connect(DB_PATH) as connection:
        total = count_chunks(connection)
        indexed = connection.execute(
            "SELECT COUNT(*) FROM chunks WHERE embedding_json IS NOT NULL"
        ).fetchone()[0]
    return total > 0 and indexed == total, total


st.set_page_config(
    page_title="Local RAG Assistant",
    page_icon="🧠",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp { background: #f6f8fb; }
      .block-container { max-width: 1080px; padding-top: 2.4rem; }
      [data-testid="stSidebar"] { background: #0f172a; }
      [data-testid="stSidebar"] * { color: #f8fafc; }
      .hero {
        background: linear-gradient(135deg, #0f172a 0%, #172554 62%, #075985 100%);
        border-radius: 24px;
        color: white;
        padding: 2.4rem 2.6rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 18px 55px rgba(15, 23, 42, .18);
      }
      .hero-kicker { color: #7dd3fc; font-size: .85rem; font-weight: 700; letter-spacing: .12em; }
      .hero h1 { color: white; font-size: 2.7rem; margin: .35rem 0 .55rem; }
      .hero p { color: #dbeafe; font-size: 1.05rem; margin: 0; max-width: 720px; }
      .source-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #0284c7;
        border-radius: 12px;
        padding: .85rem 1rem;
        margin: .55rem 0;
      }
      .answer-card {
        background: white;
        border: 1px solid #dbeafe;
        border-radius: 18px;
        color: #0f172a;
        line-height: 1.65;
        padding: 1.25rem 1.35rem;
        box-shadow: 0 8px 28px rgba(15, 23, 42, .06);
      }
      .source-card { color: #0f172a; }
      div.stButton > button { border-radius: 10px; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

ready, chunk_count = knowledge_base_status()

with st.sidebar:
    st.header("Sistem durumu")
    st.write("🟢 Bilgi bankası hazır" if ready else "🟠 İndeks hazır değil")
    st.metric("Belge parçası", chunk_count)
    st.caption(f"Cevap modeli: {DEFAULT_MODEL}")
    st.divider()
    st.subheader("Nasıl çalışır?")
    st.write("1. Soru yerelde aranır")
    st.write("2. En ilgili parçalar bulunur")
    st.write("3. Foundry Local cevap üretir")
    st.caption("Belge ve sorular cihazdan dışarı çıkmaz.")

st.markdown(
    """
    <section class="hero">
      <div class="hero-kicker">MICROSOFT FOUNDRY LOCAL · RAG</div>
      <h1>Belgelerine sor, kaynağını gör.</h1>
      <p>PDF belgelerini yerel olarak tarayan, ilgili bölümleri bulan ve cevabı kaynak sayfalarıyla birlikte üreten cihaz içi asistan.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

if not ready:
    st.warning(
        "Bilgi bankası henüz hazır değil. Önce `python ingest.py`, sonra "
        "`python index_embeddings.py` komutlarını çalıştır."
    )

st.subheader("Bir soru sor")
question = st.text_input(
    "Soru",
    value=EXAMPLE_QUESTIONS[0],
    placeholder="Örnek: Projenin 4. hafta hedefi nedir?",
    label_visibility="collapsed",
)

with st.expander("Örnek sorular"):
    for example in EXAMPLE_QUESTIONS:
        st.code(example, language=None)

ask = st.button("Yerel asistana sor", type="primary", disabled=not ready)

if ask:
    if not question.strip():
        st.error("Önce bir soru yazmalısın.")
    else:
        with st.spinner("Yerel modeller çalışıyor; ilk cevap biraz sürebilir..."):
            try:
                answer, sources = answer_from_knowledge_base(
                    question.strip(),
                    DB_PATH,
                )
            except Exception as exc:  # Streamlit kullanıcısına düzgün hata göster.
                st.error(f"Cevap üretilirken hata oluştu: {exc}")
            else:
                st.subheader("Cevap")
                st.markdown(
                    f'<div class="answer-card">{answer}</div>',
                    unsafe_allow_html=True,
                )
                st.subheader("Kullanılan kaynaklar")
                for source in sources:
                    page = source["page"] if source["page"] is not None else "-"
                    st.markdown(
                        '<div class="source-card">'
                        f'<strong>{source["source"]}</strong><br>'
                        f'Sayfa {page} · İlgi puanı {float(source["score"]):.3f}'
                        "</div>",
                        unsafe_allow_html=True,
                    )

st.caption(
    "MVP notu: Kaynak belge İngilizce olduğu için cevaplar güvenilirlik "
    "amacıyla İngilizce üretilir; Türkçe sorular arama için yerelde çevrilir."
)
