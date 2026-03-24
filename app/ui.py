from __future__ import annotations

import pandas as pd
import streamlit as st


def apply_page_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(242,143,59,0.14), transparent 24%),
                radial-gradient(circle at top left, rgba(11,92,122,0.18), transparent 30%),
                linear-gradient(180deg, #f7f5ef 0%, #eef2f3 100%);
        }
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        .page-hero {
            padding: 1.2rem 1.35rem;
            border-radius: 20px;
            color: #f7f5ef;
            background: linear-gradient(135deg, #12343b 0%, #0b5c7a 56%, #f28f3b 100%);
            box-shadow: 0 16px 38px rgba(18, 52, 59, 0.16);
            margin-bottom: 1rem;
        }
        .page-title {
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 0.25rem;
        }
        .page-copy {
            opacity: 0.92;
            font-size: 0.98rem;
        }
        .mini-card {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(18,52,59,0.08);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            min-height: 116px;
        }
        .mini-label {
            color: #5a6a70;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .mini-value {
            color: #12343b;
            font-size: 1.55rem;
            font-weight: 700;
            margin: 0.2rem 0 0.25rem 0;
        }
        .mini-copy {
            color: #355159;
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_hero(title: str, description: str) -> None:
    apply_page_theme()
    st.markdown(
        f"""
        <div class="page-hero">
            <div class="page-title">{title}</div>
            <div class="page-copy">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat_cards(cards: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(cards))
    for col, (label, value, copy) in zip(cols, cards):
        col.markdown(
            f"""
            <div class="mini-card">
                <div class="mini-label">{label}</div>
                <div class="mini-value">{value}</div>
                <div class="mini-copy">{copy}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_download(data: pd.DataFrame, label: str, file_name: str) -> None:
    st.download_button(
        label,
        data.to_csv(index=False).encode("utf-8"),
        file_name=file_name,
        mime="text/csv",
    )
