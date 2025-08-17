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

def calculate_customer_churn(monthly_data, onboarding_data):
    """Calculate customer churn metrics based on monthly data"""
    if not monthly_data:
        return []
    
    churn_data = []
    prev_active = onboarding_data['initial_customers']
    
    for i, month in enumerate(monthly_data):
        current_active = month['active_customers']
        new_customers = month['new_customers']
        
        # Calculate churned customers
        # Logic: Previous Active + New - Churned = Current Active
        # Therefore: Churned = Previous Active + New - Current Active
        churned_customers = prev_active + new_customers - current_active
        
        # Ensure churned customers can't be negative (data integrity check)
        churned_customers = max(0, churned_customers)
        
        # Calculate churn rate (% of customers lost from previous period)
        churn_rate = (churned_customers / prev_active * 100) if prev_active > 0 else 0
        
        # Calculate net customer growth
        net_growth = current_active - prev_active
        
        churn_data.append({
            "date": month['date'],
            "previous_active": prev_active,
            "new_customers": new_customers,
            "churned_customers": churned_customers,
            "current_active": current_active,
            "churn_rate": churn_rate,
            "net_growth": net_growth
        })
        
        prev_active = current_active
    
    return churn_data

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
        
        # Calculate customer churn data
        churn_data = calculate_customer_churn(monthly_data, onboarding)
        latest_churn = churn_data[-1] if churn_data else None
        
        summary += f"""
- Latest Monthly Revenue: ₱{latest_month['revenue']:,.2f}
- Latest Monthly Expenses: ₱{total_latest_expenses:,.2f}
- Current Customers: {latest_month['active_customers']}
- Employees: {onboarding['current_employees']}

PROGRESS vs PLAN:
- Revenue: ₱{latest_month['revenue']:,.2f} vs ₱{onboarding['target_revenue']:,.2f} planned ({((latest_month['revenue'] - onboarding['target_revenue']) / onboarding['target_revenue'] * 100) if onboarding['target_revenue'] > 0 else 0:+.1f}%)
- Customers: {latest_month['active_customers']} vs {onboarding['initial_customers']} initial ({latest_month['active_customers'] - onboarding['initial_customers']:+} change)"""
        
        if latest_churn:
            summary += f"""

CUSTOMER METRICS (Latest Month):
- New Customers: +{latest_churn['new_customers']}
- Churned Customers: -{latest_churn['churned_customers']}
- Net Growth: {latest_churn['net_growth']:+}
- Churn Rate: {latest_churn['churn_rate']:.1f}%"""
    
    return summary

@tool
def analyze_customer_churn():
    """Analyze customer churn patterns and retention metrics"""
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()
    
    if not monthly_data:
        return "No monthly data available to analyze customer churn."
    
    churn_data = calculate_customer_churn(monthly_data, onboarding)
    
    if not churn_data:
        return "Insufficient data to calculate churn metrics."
    
    # Calculate overall metrics
    total_new_customers = sum(month['new_customers'] for month in churn_data)
    total_churned_customers = sum(month['churned_customers'] for month in churn_data)
    avg_churn_rate = sum(month['churn_rate'] for month in churn_data) / len(churn_data)
    
    # Recent performance (last 3 months)
    recent_months = churn_data[-3:] if len(churn_data) >= 3 else churn_data
    recent_avg_churn = sum(month['churn_rate'] for month in recent_months) / len(recent_months)
    recent_net_growth = sum(month['net_growth'] for month in recent_months)
    
    # Customer retention rate (inverse of churn)
    retention_rate = 100 - avg_churn_rate
    recent_retention_rate = 100 - recent_avg_churn
    
    analysis = f"""CUSTOMER CHURN ANALYSIS - {onboarding['startup_name']}

OVERALL METRICS ({len(churn_data)} months):
- Total New Customers: {total_new_customers}
- Total Churned Customers: {total_churned_customers}
- Average Churn Rate: {avg_churn_rate:.1f}%/month
- Average Retention Rate: {retention_rate:.1f}%/month
- Net Customer Growth: {churn_data[-1]['current_active'] - onboarding['initial_customers']:+}

RECENT PERFORMANCE (last {len(recent_months)} months):
- Average Churn Rate: {recent_avg_churn:.1f}%/month
- Average Retention Rate: {recent_retention_rate:.1f}%/month
- Net Growth: {recent_net_growth:+} customers

MONTHLY BREAKDOWN:"""
    
    for month in churn_data[-6:]:  # Show last 6 months
        analysis += f"""
{month['date']}: {month['previous_active']} → {month['current_active']} ({month['net_growth']:+})
  New: +{month['new_customers']}, Churned: -{month['churned_customers']}, Churn Rate: {month['churn_rate']:.1f}%"""
    
    # Health assessment
    analysis += "\n\nCHURN HEALTH ASSESSMENT:"
    if recent_avg_churn < 5:
        analysis += "\n✅ EXCELLENT: Very low churn rate"
    elif recent_avg_churn < 10:
        analysis += "\n👍 GOOD: Healthy churn rate"
    elif recent_avg_churn < 20:
        analysis += "\n⚠️ CONCERNING: High churn rate - investigate retention"
    else:
        analysis += "\n❌ CRITICAL: Very high churn rate - immediate action needed"
    
    return analysis

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
- Actual burn rate: ₱{avg_actual_burn:,.2f}/month ({len(recent_months)}-month average)
- Variance: ₱{avg_actual_burn - planned_burn:+,.2f}/month ({((avg_actual_burn - planned_burn) / planned_burn * 100):+.1f}%)"""

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
        return f"🎉 You are cash positive! Generating ₱{abs(net_burn):,.2f}/month in positive cash flow\nCurrent cash: ₱{current_cash:,.2f}"
    
    runway = math.floor(current_cash / net_burn)
    
    return f"""Current runway: {runway} months
- Current cash: ₱{current_cash:,.2f}
- Average monthly revenue: ₱{avg_revenue:,.2f}
- Average monthly expenses: ₱{avg_expenses:,.2f}
- Net monthly burn: ₱{net_burn:,.2f}
({len(recent_months)} month average)"""

@tool
def compute_cac():
    """
    Compute the Customer Acquisition Cost (CAC) based on historical data.
    CAC = Total Marketing Expenses / New Customers Acquired (for a given period)
    """
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()

    if not monthly_data:
        return "No monthly financial data available to compute CAC."

    # --- Lifetime CAC ---
    total_marketing = sum(month['marketing_expenses'] for month in monthly_data)
    total_new_customers = sum(month['new_customers'] for month in monthly_data)
    lifetime_cac = (total_marketing / total_new_customers) if total_new_customers > 0 else float('inf')

    # --- Recent CAC (last 3 months) ---
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    recent_marketing = sum(month['marketing_expenses'] for month in recent_months)
    recent_new_customers = sum(month['new_customers'] for month in recent_months)
    recent_cac = (recent_marketing / recent_new_customers) if recent_new_customers > 0 else float('inf')

    # Format for display
    lifetime_cac_display = "∞ (No customers acquired yet)" if lifetime_cac == float('inf') else f"₱{lifetime_cac:,.2f}"
    recent_cac_display = "∞ (No customers acquired in period)" if recent_cac == float('inf') else f"₱{recent_cac:,.2f}"

    return f"""CUSTOMER ACQUISITION COST (CAC) - {onboarding['startup_name']}

ACQUISITION METRICS:
- Lifetime CAC: {lifetime_cac_display}
- Recent CAC (last {len(recent_months)} months): {recent_cac_display}
- Lifetime marketing spend: ₱{total_marketing:,.2f}
- Lifetime new customers acquired: {total_new_customers}
- Recent marketing spend: ₱{recent_marketing:,.2f}
- Recent new customers: {recent_new_customers}"""

def calculate_cac_helper(monthly_data, months=3):
    """Helper function to calculate CAC without being a tool"""
    if not monthly_data:
        return float('inf'), 0, 0
    
    recent_months = monthly_data[-months:] if len(monthly_data) >= months else monthly_data
    recent_marketing = sum(month['marketing_expenses'] for month in recent_months)
    recent_new_customers = sum(month['new_customers'] for month in recent_months)
    recent_cac = (recent_marketing / recent_new_customers) if recent_new_customers > 0 else float('inf')
    
    return recent_cac, recent_marketing, recent_new_customers

@tool
def compute_customer_ltv():
    """
    Compute Customer Lifetime Value (LTV) based on revenue and churn patterns
    """
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()
    
    if not monthly_data:
        return "No monthly financial data available to compute LTV."
    
    churn_data = calculate_customer_churn(monthly_data, onboarding)
    
    if not churn_data:
        return "Insufficient data to calculate LTV metrics."
    
    # Calculate average revenue per customer per month
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    avg_revenue = sum(month['revenue'] for month in recent_months) / len(recent_months)
    avg_active_customers = sum(month['active_customers'] for month in recent_months) / len(recent_months)
    
    arpu = avg_revenue / avg_active_customers if avg_active_customers > 0 else 0
    
    # Calculate average customer lifespan (1 / churn rate)
    recent_churn_data = churn_data[-3:] if len(churn_data) >= 3 else churn_data
    avg_monthly_churn_rate = sum(month['churn_rate'] for month in recent_churn_data) / len(recent_churn_data) / 100
    
    # Customer lifespan in months
    customer_lifespan = (1 / avg_monthly_churn_rate) if avg_monthly_churn_rate > 0 else float('inf')
    
    # LTV = ARPU × Customer Lifespan
    ltv = arpu * customer_lifespan if customer_lifespan != float('inf') else float('inf')
    
    # Calculate CAC using helper function
    recent_cac, recent_marketing, recent_new_customers = calculate_cac_helper(monthly_data, 3)
    
    ltv_cac_ratio = (ltv / recent_cac) if recent_cac != float('inf') and recent_cac > 0 else float('inf')
    
    ltv_display = f"₱{ltv:,.2f}" if ltv != float('inf') else "∞ (No churn detected)"
    lifespan_display = f"{customer_lifespan:.1f} months" if customer_lifespan != float('inf') else "∞ (No churn)"
    ratio_display = f"{ltv_cac_ratio:.1f}:1" if ltv_cac_ratio != float('inf') else "∞:1"
    recent_cac_display = f"₱{recent_cac:,.2f}" if recent_cac != float('inf') else "∞"
    
    analysis = f"""CUSTOMER LIFETIME VALUE (LTV) - {onboarding['startup_name']}

LTV CALCULATION:
- Average Revenue Per Customer (ARPU): ₱{arpu:,.2f}/month
- Average Customer Lifespan: {lifespan_display}
- Customer Lifetime Value: {ltv_display}

LTV:CAC ANALYSIS:
- LTV: {ltv_display}
- CAC: {recent_cac_display}
- LTV:CAC Ratio: {ratio_display}
- Recent marketing spend: ₱{recent_marketing:,.2f}
- Recent new customers: {recent_new_customers}

HEALTH ASSESSMENT:"""
    
    if ltv_cac_ratio >= 3:
        analysis += "\n✅ EXCELLENT: Strong LTV:CAC ratio"
    elif ltv_cac_ratio >= 2:
        analysis += "\n👍 GOOD: Healthy unit economics"
    elif ltv_cac_ratio >= 1:
        analysis += "\n⚠️ CONCERNING: Break-even unit economics"
    else:
        analysis += "\n❌ CRITICAL: Negative unit economics"
    
    return analysis

@tool
def analyze_hiring_affordability(role="developer", monthly_salary=None, months_ahead=6):
    """Analyze if startup can afford to hire new employee(s) with given salary
    
    Args:
        role: Job role title (used for display purposes only)
        monthly_salary: Required monthly salary amount
        months_ahead: Number of months to project costs
    """
    if monthly_salary is None:
        raise ValueError(f"Monthly salary must be provided for {role} position. Please specify the salary amount.")
    
    onboarding = get_onboarding_data()
    monthly_data = get_monthly_financial_data()
    current_cash, _ = calculate_current_cash()
    
    # Calculate current burn rate
    if monthly_data:
        latest = monthly_data[-1]
        current_burn = (latest['product_dev_expenses'] + latest['manpower_expenses'] + 
                       latest['marketing_expenses'] + latest['operations_expenses'] + latest['other_expenses'])
        current_revenue = latest['revenue']
    else:
        current_burn = (onboarding['planned_product_dev'] + onboarding['planned_manpower'] + 
                       onboarding['planned_marketing'] + onboarding['planned_operations'])
        current_revenue = onboarding['target_revenue']
    
    net_burn = current_burn - current_revenue
    current_runway = math.floor(current_cash / net_burn) if net_burn > 0 else float('inf')
    
    # Calculate impact of new hire
    new_burn = current_burn + monthly_salary
    new_net_burn = new_burn - current_revenue
    new_runway = math.floor(current_cash / new_net_burn) if new_net_burn > 0 else float('inf')
    runway_impact = new_runway - current_runway if current_runway != float('inf') else 0
    
    # Additional hiring costs (benefits, equipment, onboarding)
    total_monthly_cost = monthly_salary
    
    analysis = f"""HIRING AFFORDABILITY ANALYSIS - {role.title()}:

SALARY IMPACT:
- Base monthly salary: ₱{monthly_salary:,.2f}
- Total monthly cost: ₱{total_monthly_cost:,.2f}

RUNWAY IMPACT:
- Current runway: {current_runway if current_runway != float('inf') else '∞'} months
- New runway with hire: {new_runway if new_runway != float('inf') else '∞'} months
- Impact: {runway_impact:+} months

AFFORDABILITY ASSESSMENT:"""
    
    if new_runway >= 12 or new_runway == float('inf'):
        analysis += "\n✅ AFFORDABLE: Still maintains healthy runway"
    elif new_runway >= 6:
        analysis += "\n⚠️ RISKY: Runway becomes concerning, consider timing"
    else:
        analysis += "\n❌ NOT AFFORDABLE: Would create dangerous runway situation"
    
    # Cost per month for different time periods
    analysis += f"\n\nCOST PROJECTION ({months_ahead} months):"
    analysis += f"\n- Total cost: ₱{total_monthly_cost * months_ahead:,.2f}"
    analysis += f"\n- Cash remaining: ₱{current_cash - (total_monthly_cost * months_ahead):,.2f}"
    
    return analysis

tools = [
    get_financial_summary, 
    analyze_customer_churn, 
    compute_burn_rate, 
    compute_runway,
    compute_cac,
    compute_customer_ltv,
    analyze_hiring_affordability
]