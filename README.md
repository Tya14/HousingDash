# Singapore HDB Resale Dashboard

**Live App:** https://housingdash-hfjkswgesykxjzxutwudv3.streamlit.app/

An interactive data analytics dashboard built with Streamlit to explore trends in Singapore’s HDB resale market (2005 – Feb 2012).  

---

## Preview


https://github.com/user-attachments/assets/6c916f6f-a41d-45a3-a065-b75f5a7b559e


![Dashboard Preview](screenshot.png)

---

## Project Overview

This dashboard enables users to explore resale flat transactions across towns, flat types, price ranges, and time periods.  

### Key questions :
- How have resale prices changed over time?
- Which towns have higher average resale prices?
- How do flat types and sizes influence pricing?
- What patterns emerge across years and storey ranges?

---

## Features

- Interactive filters (town, flat type, price, floor area, year)
- Time-series analysis of resale prices (quarterly and yearly)
- KPI metrics (median price, average price per sqm, transaction volume)
- Town-level price comparisons
- Scatter plots, histograms, and heatmaps
- SQL-powered aggregations using an in-memory SQLite database
- Export functionality for filtered datasets

---

## Tech Stack

- Python  
- Streamlit (dashboard framework)  
- Pandas (data processing)  
- SQLite (in-memory query engine)  
- Plotly (interactive visualisations)  

---

## Dataset

- Source: Singapore Government Open Data Portal (data.gov.sg)  
  https://data.gov.sg/datasets/d_43f493c6c50d54243cc1eab0df142d6a  
- Provider: Housing & Development Board (HDB)  
- Original time range: January 2001 – February 2012  

Due to file size constraints for deployment, the dataset was truncated to include transactions from **2005 – 2012**.  
This subset preserves recent market trends while ensuring efficient loading and responsiveness in the deployed application.


### Key fields:
- Town  
- Flat type and model  
- Floor area (sqm)  
- Storey range  
- Lease commencement year  
- Resale price  

---

## How It Works

1. The raw dataset is loaded into an in-memory SQLite database  
2. Sidebar filters dynamically construct SQL queries  
3. All aggregations are computed using SQL (no pandas filtering at query stage)  
4. Results are visualised using Plotly within Streamlit  

### Design considerations:
- Efficient querying for larger datasets  
- Clear separation between data processing and presentation  
- Scalable and responsive dashboard performance  

---

## Running the App Locally

### 1. Clone the repository
```bash
git clone https://github.com/Tya14/HousingDash.git
cd hdb-resale-dashboard
