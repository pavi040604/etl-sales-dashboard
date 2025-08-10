import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import io
from src import config

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    layout="wide",
    page_title="Enterprise Sales Dashboard",
    page_icon="📊"
)

# ---------------------------
# Load Data
# ---------------------------
@st.cache_data
def load_data():
    engine = create_engine(config.DB_URL)
    df = pd.read_sql("SELECT * FROM sales", engine)
    # Ensure date parsing works with DD/MM/YYYY formats
    df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True, errors="coerce")
    return df

df = load_data()

st.title("📊 Enterprise Sales Dashboard")
st.write(f"Rows loaded: {len(df)}")

# ---------------------------
# Filters
# ---------------------------
regions = st.multiselect(
    "Select Region(s):",
    options=df["region"].dropna().unique(),
    default=df["region"].dropna().unique()
)

categories = st.multiselect(
    "Select Category:",
    options=df["category"].dropna().unique(),
    default=df["category"].dropna().unique()
)

min_date = df["order_date"].min()
max_date = df["order_date"].max()

date_range = st.date_input(
    "Select Date Range:",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# ---------------------------
# Apply Filters
# ---------------------------
mask = (
    df["region"].isin(regions) &
    df["category"].isin(categories) &
    df["order_date"].between(
        pd.to_datetime(date_range[0]),
        pd.to_datetime(date_range[1])
    )
)
filtered_df = df.loc[mask]

# ---------------------------
# KPIs
# ---------------------------
total_sales = filtered_df['sales'].sum()
avg_order_value = filtered_df['sales'].mean()
unique_customers = filtered_df['customer_id'].nunique()
top_product = filtered_df.groupby('product_name')['sales'].sum().idxmax() if not filtered_df.empty else "N/A"
region_share = (filtered_df.groupby('region')['sales'].sum() / total_sales * 100).round(2) if total_sales > 0 else pd.Series()
best_region = region_share.idxmax() if not region_share.empty else "N/A"

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Sales", f"${total_sales:,.2f}")
col2.metric("Avg Order Value", f"${avg_order_value:,.2f}")
col3.metric("Customers", unique_customers)
col4.metric("Top Product", top_product)
col5.metric("Best Region", best_region)

# ---------------------------
# Charts
# ---------------------------
if not filtered_df.empty:
    sales_region = filtered_df.groupby("region")["sales"].sum().reset_index()
    fig_region = px.bar(sales_region, x="region", y="sales", title="Sales by Region")
    st.plotly_chart(fig_region, use_container_width=True)

    monthly_sales = (
        filtered_df.groupby(filtered_df["order_date"].dt.to_period("M"))["sales"]
        .sum()
        .reset_index()
    )
    monthly_sales["order_date"] = monthly_sales["order_date"].astype(str)
    fig_month = px.line(monthly_sales, x="order_date", y="sales", title="Monthly Sales Trend")
    st.plotly_chart(fig_month, use_container_width=True)
else:
    st.warning("No data matches the selected filters.")

# ---------------------------
# Export Options
# ---------------------------
st.subheader("📥 Export Data")

# CSV
csv_buffer = io.StringIO()
filtered_df.to_csv(csv_buffer, index=False)
st.download_button(
    label="Download as CSV",
    data=csv_buffer.getvalue(),
    file_name="filtered_sales.csv",
    mime="text/csv"
)

# Excel
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
    filtered_df.to_excel(writer, index=False, sheet_name='Sales')
st.download_button(
    label="Download as Excel",
    data=excel_buffer,
    file_name="filtered_sales.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
