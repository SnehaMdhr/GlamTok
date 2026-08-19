# GlamTok - Nepal TikTok Fashion Engagement Predictor

A thesis project that predicts social media engagement and recommends the best times to post for fashion businesses in Nepal, using machine learning on scraped TikTok data. It ships as a full-stack analytics dashboard called GlamTok.

## Project Overview

- Scrapes TikTok post data from 13 Nepali fashion businesses (Jan 2024 - Jul 2026) using Selenium.
- Predicts an engagement score: `(likes + 3*comments + 2*shares + saves) / views`.
- Compares Random Forest and XGBoost models with SHAP explainability.
- Provides a dashboard showing a 24x7 engagement heatmap and top-3 recommended posting times.

## Architecture

| Folder | Purpose |
|---|---|
| `data_scrapping/` | Selenium scrapers for TikTok, Instagram and Facebook. |
| `data_cleaning/` | Cleaning, feature engineering, outlier removal and synthetic augmentation. |
| `machine_learning/` | Model training (step1-step5), SHAP analysis and analytics scripts. |
| `backend/` | Express API gateway and FastAPI ML microservice. |
| `frontend/` | React (Create React App) dashboard. |

## Pipeline

1. **Scraping:** collect views, likes, comments, shares, saves, duration, captions, hashtags and post timestamps.
2. **Cleaning:** normalize columns, anonymize businesses, cap outliers, engineer time and calendar features.
3. **Modeling:** time-based train/test split, tune Random Forest and XGBoost, pick the winner, explain with SHAP.
4. **Backend:** Express API (port 5000) calls FastAPI ML service (port 8001) to score all 168 hour x day combinations.
5. **Frontend:** React dashboard with predict, descriptive, diagnostic, predictive and prescriptive pages.

## Getting Started

```bash
# 1. Train the model (optional)
cd machine_learning
python step1.py && python step2.py && python step3.py && python step4.py && python step5.py

# 2. Precompute the API cache
cd backend
python precompute_cache.py

# 3. Start the ML service
uvicorn ml_service:app --port 8001

# 4. Start the Express API
node server.js          # http://localhost:5000

# 5. Start the frontend
cd frontend
npm install
npm start               # http://localhost:3000
```

## Key Findings

- Timing matters more than account size.
- Midnight to 3:00 NPT gets the highest average likes.
- 4-7 hashtags, 50-150 character captions and 15-30 second videos perform best.
- Festival months get more posts but not better engagement.

## Notes

- All times are NPT (Nepal Time).
- Business names are anonymized in cleaned datasets.
- Scraped data files and generated outputs are git-ignored.