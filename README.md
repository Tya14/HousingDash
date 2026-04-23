# Singapore HDB Resale Dashboard

An interactive data analytics dashboard built with Streamlit to explore trends in Singapore’s HDB resale market (2000 – Feb 2012).  

---

## Project Overview

This dashboard enables users to explore resale flat transactions across towns, flat types, price ranges, and time periods.  

### Key questions:
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
  - [Resale Flat Prices (Based on Approval Date), 2000 – Feb 2012](https://data.gov.sg/datasets/d_43f493c6c50d54243cc1eab0df142d6a/view?utm_source=chatgpt.com)  
- Provider: Housing & Development Board (HDB)  
- Time range: January 2000 – February 2012 :contentReference[oaicite:1]{index=1}  

This dataset contains historical resale flat transaction records, including details such as:
- Town  
- Flat type and model  
- Floor area (sqm)  
- Storey range  
- Lease commencement year  
- Resale price  

---

## How It Works

1. The raw CSV dataset is loaded into an in-memory SQLite database  
2. Sidebar filters dynamically construct SQL queries  
3. All aggregations are computed using SQL (no pandas filtering at query stage)  
4. Results are visualised using Plotly within Streamlit  

### Design considerations:
- Efficient querying for larger datasets  
- Clear separation between data processing and presentation  
- Scalable and responsive dashboard performance  

---

## Running the App

### 1. Clone the repository
```bash
git clone https://github.com/your-username/hdb-resale-dashboard.git
cd hdb-resale-dashboard
