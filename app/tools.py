from db import get_connection
from langchain.tools import tool
import math
def get_onboarding_data():
    """Helper function to retrieve initial financial data (baseline/expected cashflow)"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            startup_name,
            industry,
            target_revenue,
            product_dev_expenses as planned_product_dev,
            manpower_expenses as planned_manpower,
            marketing_expenses as planned_marketing,
            operations_expenses as planned_operations,
            initial_cash,
            initial_customers,
            current_employees,
            target_runway_months,
            onboarding_date
        FROM onboarding_data
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    return {
        "startup_name": row[0],
        "industry": row[1],
        "target_revenue": float(row[2]),
        "planned_product_dev": float(row[3]),
        "planned_manpower": float(row[4]),
        "planned_marketing": float(row[5]),
        "planned_operations": float(row[6]),
        "initial_cash": float(row[7]),
        "initial_customers": int(row[8]),
        "current_employees": int(row[9]),
        "target_runway_months": int(row[10]),
        "onboarding_date": row[11]
    }

def get_monthly_financial_data():
    """Helper function to retrieve monthly iterations of financial data"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            date,
            revenue,
            product_dev_expenses,
            manpower_expenses,
            marketing_expenses,
            operations_expenses,
            new_customers,
            active_customers,
            other_expenses
        FROM monthly_financial_data
        ORDER BY date ASC  -- Chronological order from onboarding
    """)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    monthly_data = []
    for row in rows:
        monthly_data.append({
            "date": row[0],
            "revenue": float(row[1]),
            "product_dev_expenses": float(row[2]),
            "manpower_expenses": float(row[3]),
            "marketing_expenses": float(row[4]),
            "operations_expenses": float(row[5]),
            "new_customers": int(row[6]),
            "active_customers": int(row[7]),
            "other_expenses": float(row[8])
        })
    
    return monthly_data

def calculate_current_cash():
    """Calculate current cash based on initial cash + all monthly cash flows"""
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()
    
    current_cash = onboarding['initial_cash']
    
    for month in monthly_data:
        total_expenses = (month['product_dev_expenses'] + 
                         month['manpower_expenses'] + 
                         month['marketing_expenses'] + 
                         month['operations_expenses'] + 
                         month['other_expenses'])
        
        monthly_cash_flow = month['revenue'] - total_expenses
        current_cash += monthly_cash_flow
    
    return current_cash, len(monthly_data)  # Return cash and months elapsed

@tool
def get_financial_summary():
    """Retrieve complete financial journey from onboarding to current state"""
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()
    current_cash, months_elapsed = calculate_current_cash()
    
    summary = f"""FINANCIAL JOURNEY - {onboarding['startup_name']} ({onboarding['industry']})

STARTING POSITION (Onboarding):
- Initial Cash: ₱{onboarding['initial_cash']:,.2f}
- Planned Monthly Revenue: ₱{onboarding['target_revenue']:,.2f}
- Planned Expenses: ₱{onboarding['planned_product_dev'] + onboarding['planned_manpower'] + onboarding['planned_marketing'] + onboarding['planned_operations']:,.2f}/month
- Initial Customers: {onboarding['initial_customers']}
- Target Runway: {onboarding['target_runway_months']} months

CURRENT POSITION ({months_elapsed} months later):
- Current Cash: ₱{current_cash:,.2f}"""

    if monthly_data:
        latest_month = monthly_data[-1]
        total_latest_expenses = (latest_month['product_dev_expenses'] + 
                               latest_month['manpower_expenses'] + 
                               latest_month['marketing_expenses'] + 
                               latest_month['operations_expenses'] + 
                               latest_month['other_expenses'])
        
        summary += f"""
- Latest Monthly Revenue: ₱{latest_month['revenue']:,.2f}
- Latest Monthly Expenses: ₱{total_latest_expenses:,.2f}
- Current Customers: {latest_month['active_customers']}
- Employees: {onboarding['current_employees']}

PROGRESS vs PLAN:
- Revenue: ₱{latest_month['revenue']:,.2f} vs ₱{onboarding['target_revenue']:,.2f} planned ({((latest_month['revenue'] - onboarding['target_revenue']) / onboarding['target_revenue'] * 100) if onboarding['target_revenue'] > 0 else 0:+.1f}%)
- Customers: {latest_month['active_customers']} vs {onboarding['initial_customers']} initial ({latest_month['active_customers'] - onboarding['initial_customers']:+} change)"""
    
    return summary

@tool
def compute_burn_rate():
    """Compute current burn rate and compare with initial projections"""
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()
    
    planned_burn = (onboarding['planned_product_dev'] + onboarding['planned_manpower'] + 
                   onboarding['planned_marketing'] + onboarding['planned_operations'])
    
    if not monthly_data:
        return f"Planned monthly burn rate: ₱{planned_burn:,.2f}\n(No actual data available yet)"
    
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    
    actual_burns = []
    for month in recent_months:
        total_expenses = (month['product_dev_expenses'] + month['manpower_expenses'] + 
                         month['marketing_expenses'] + month['operations_expenses'] + month['other_expenses'])
        actual_burns.append(total_expenses)
    
    avg_actual_burn = sum(actual_burns) / len(actual_burns)
    
    return f"""BURN RATE ANALYSIS:
- Planned burn rate: ₱{planned_burn:,.2f}/month
- Actual burn rate: ₱{avg_actual_burn:,.2f}/month ({len(recent_months)}-month average)"""

@tool
def compute_runway(simulated_expense=None):
    """Compute current runway based on actual cash position and recent burn rate"""
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()
    current_cash, months_elapsed = calculate_current_cash()
    
    if simulated_expense is not None:
        runway = math.floor(current_cash / simulated_expense)
        return f"Simulated runway: {runway} months (₱{current_cash:,.2f} ÷ ₱{simulated_expense:,.2f}/month)"
    
    if not monthly_data:
        planned_burn = (onboarding['planned_product_dev'] + onboarding['planned_manpower'] + 
                       onboarding['planned_marketing'] + onboarding['planned_operations'])
        runway = math.floor(current_cash / planned_burn) if planned_burn > 0 else float('inf')
        return f"Current runway: {runway} months (₱{current_cash:,.2f} ÷ ₱{planned_burn:,.2f}/month planned burn)\nNote: Based on projected expenses - no actual monthly data yet"
    
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    
    avg_revenue = sum(month['revenue'] for month in recent_months) / len(recent_months)
    avg_expenses = sum(month['product_dev_expenses'] + month['manpower_expenses'] + 
                      month['marketing_expenses'] + month['operations_expenses'] + month['other_expenses'] 
                      for month in recent_months) / len(recent_months)
    
    net_burn = avg_expenses - avg_revenue
    
    if net_burn <= 0:
        return f"🎉 You are cash positive this month! Generating ₱{abs(net_burn):,.2f}/month in positive cash flow\nCurrent cash: ₱{current_cash:,.2f}"
    
    runway = math.floor(current_cash / net_burn)
    
    return f"""Current runway: {runway} months
- Current cash: ₱{current_cash:,.2f}
- Average monthly revenue: ₱{avg_revenue:,.2f}
- Average monthly expenses: ₱{avg_expenses:,.2f}
- Net monthly burn: ₱{net_burn:,.2f}
({len(recent_months)} month average)"""

tools = [get_financial_summary, get_monthly_financial_data, calculate_current_cash, compute_burn_rate, compute_runway]