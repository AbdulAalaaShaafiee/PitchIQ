"""Synchronized highlights demo for the 2026 FIFA World Cup Final."""
import streamlit as st

from pitchiq.world_cup_demo import render_world_cup_final_demo

st.set_page_config(
    page_title="World Cup Final Demo | PitchIQ",
    page_icon="⚽",
    layout="wide",
)

render_world_cup_final_demo()
