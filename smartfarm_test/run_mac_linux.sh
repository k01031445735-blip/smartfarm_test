#!/bin/bash
cd "$(dirname "$0")"
pip install -q streamlit pandas numpy matplotlib
streamlit run app.py
