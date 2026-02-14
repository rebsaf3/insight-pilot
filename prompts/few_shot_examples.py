"""Few-shot examples for code generation quality."""

EXAMPLES = [
    {
        "profile_summary": "Dataset: 500 rows x 4 columns\n- date (datetime): 0 nulls, 365 unique\n- revenue (numeric): 3 nulls, range 100-99999, mean 12345\n- category (categorical): 0 nulls, 3 unique [Electronics, Clothing, Food]\n- quantity (numeric): 0 nulls, range 1-500, mean 45",
        "user_prompt": "Show me monthly revenue trends by category",
        "code": '''# Convert date and extract month
df['date'] = pd.to_datetime(df['date'])
df['month'] = df['date'].dt.to_period('M').astype(str)

# Group by month and category, sum revenue
monthly = df.groupby(['month', 'category'])['revenue'].sum().reset_index()

fig = px.line(
    monthly, x='month', y='revenue', color='category',
    title='Monthly Revenue Trends by Category',
    labels={'month': 'Month', 'revenue': 'Revenue ($)', 'category': 'Category'}
)
fig.update_layout(xaxis_tickangle=-45, hovermode='x unified')''',
    },
    {
        "profile_summary": "Dataset: 1000 rows x 3 columns\n- product (categorical): 0 nulls, 20 unique\n- sales (numeric): 0 nulls, range 50-5000\n- region (categorical): 0 nulls, 4 unique [North, South, East, West]",
        "user_prompt": "Show top 10 products by total sales as a bar chart",
        "code": '''# Calculate total sales per product
product_sales = df.groupby('product')['sales'].sum().reset_index()
top_10 = product_sales.nlargest(10, 'sales')

fig = px.bar(
    top_10, x='product', y='sales',
    title='Top 10 Products by Total Sales',
    labels={'product': 'Product', 'sales': 'Total Sales ($)'},
    color='sales', color_continuous_scale='Blues'
)
fig.update_layout(xaxis_tickangle=-45)''',
    },
    {
        "profile_summary": "Dataset: 200 rows x 5 columns\n- department (categorical): 5 unique\n- employee_count (numeric)\n- avg_salary (numeric)\n- budget (numeric)\n- satisfaction_score (numeric): range 1-10",
        "user_prompt": "Create a summary table of all departments",
        "code": '''# Create summary table
summary = df.groupby('department').agg({
    'employee_count': 'sum',
    'avg_salary': 'mean',
    'budget': 'sum',
    'satisfaction_score': 'mean'
}).reset_index()

summary.columns = ['Department', 'Employees', 'Avg Salary ($)', 'Total Budget ($)', 'Satisfaction']
summary['Avg Salary ($)'] = summary['Avg Salary ($)'].round(0).astype(int)
summary['Satisfaction'] = summary['Satisfaction'].round(1)

fig = go.Figure(data=[go.Table(
    header=dict(values=list(summary.columns), fill_color='#1E88E5', font=dict(color='white', size=13), align='left'),
    cells=dict(values=[summary[col] for col in summary.columns], fill_color='#F5F5F5', align='left')
)])
fig.update_layout(title='Department Summary')''',
    },
]
