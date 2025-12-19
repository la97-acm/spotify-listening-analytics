# Spotify Analytics Platform

End-to-end data pipeline analyzing 8+ years of Spotify listening history with interactive Streamlit dashboard.

<img width="2090" height="1062" alt="Screenshot 2025-12-19 at 6 14 36 PM" src="https://github.com/user-attachments/assets/30b76388-824d-4cab-b966-f03f6686d770" />

<img width="2090" height="1255" alt="Screenshot 2025-12-19 at 6 14 58 PM" src="https://github.com/user-attachments/assets/16409bc8-85a3-4e63-8e33-f3c6e5bec6b7" />

<img width="2090" height="1255" alt="Screenshot 2025-12-19 at 6 15 07 PM" src="https://github.com/user-attachments/assets/c0912a52-20cf-4f7a-927e-32cd4ee4199f" />

## Overview

Built this to get more insight than Spotify Wrapped provides. Processes 70K+ streams from 2017-2025, combining historical exports with live API data.

**Stack**: Python • Pandas • Apache Airflow • Streamlit • Plotly • Spotipy • Docker

## Setup

1. Get Spotify API credentials from [developer.spotify.com](https://developer.spotify.com/dashboard)
2. Copy `.env.example` to `.env` and add your credentials
3. Request your listening history from Spotify and place CSV in `data/`
4. Install dependencies: `pip install -r requirements.txt`
5. Run dashboard: `streamlit run streamlit_app.py`

## Features

- Year-over-year listening comparisons
- Top artists/tracks with album artwork
- Listening patterns by time of day and day of week
- Artist discovery timeline
- Interactive date range filtering
