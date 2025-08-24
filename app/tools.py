from db import get_connection
from langchain.tools import tool
import math
from logger import log_error


_startup_name = None

def set_startup_context(startup_name):
    """Set the global startup context for all tools"""
    global _startup_name
    _startup_name = startup_name

def get_startup_name():
    """Get the current startup name"""
    global _startup_name
    return _startup_name

def get_onboarding_data(startup_name = None):
    """Helper function to retrieve initial financial data (baseline/expected cashflow)"""
    
    if startup_name is None:
        startup_name = get_startup_name()
        
    conn, cur = None, None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                startup_name,
                industry,
                target_revenue,
                product_dev_expenses AS planned_product_dev,
                manpower_expenses AS planned_manpower,
                marketing_expenses AS planned_marketing,
                operations_expenses AS planned_operations,
                initial_cash,
                initial_customers,
                current_employees,
                target_runway_months,
                onboarding_date
            FROM onboarding_data
            WHERE startup_name = %s
            LIMIT 1
        """,(startup_name,))
        row = cur.fetchone()

        if not row:
            log_error(
            error_type="DB_ERROR",
            error_message=f"No onboarding data for startup_name {startup_name}",
            context={"function": "get_onboarding_data", "startup_name": startup_name}
        )
            return None

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

    except Exception as e:
        log_error(
            error_type="DB_ERROR",
            error_message=f"Error in get_onboarding_data: {str(e)}",
            context={"function": "get_onboarding_data", "startup_name": startup_name}
        )
        return None
    finally:
        if cur: cur.close()
        if conn: conn.close()

def get_onboarding_data_by_startup(startup_name: str):
    """Helper function to retrieve initial financial data (baseline/expected cashflow)"""
    conn, cur = None, None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(f"""
            SELECT 
                startup_name,
                industry,
                target_revenue,
                product_dev_expenses AS planned_product_dev,
                manpower_expenses AS planned_manpower,
                marketing_expenses AS planned_marketing,
                operations_expenses AS planned_operations,
                initial_cash,
                initial_customers,
                current_employees,
                target_runway_months,
                onboarding_date
            FROM onboarding_data
            WHERE startup_name = %s
            LIMIT 1
        """, (startup_name,))
        row = cur.fetchone()

        if not row:
            log_error("No onboarding_data found in DB")
            return None

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

    except Exception as e:
        log_error(
        error_type="DB_ERROR",
        error_message=f"Error in get_onboarding_data: {str(e)}",
        context={"function": "get_onboarding_data"}
    )
        return None
    finally:
        if cur: cur.close()
        if conn: conn.close()



def get_monthly_financial_data(startup_name = None):
    """Helper function to retrieve monthly iterations of financial data"""
    if startup_name is None:
        startup_name = get_startup_name()
        
    conn, cur = None, None
    try:
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
            WHERE startup_name = %s
            ORDER BY date ASC
        """,(startup_name,))
        rows = cur.fetchall()

        if not rows:
            log_error(
            error_type="DB_ERROR",
            error_message=f"No monthly_financial_data for startup_name {startup_name}",
            context={"function": "get_monthly_financial_data", "startup_id": startup_name}
        )
            return []

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

    except Exception as e:
        log_error(
            error_type="DB_ERROR",
            error_message=f"Error in get_monthly_financial_data: {str(e)}",
            context={"function": "get_monthly_financial_data", "startup_id": startup_name}
        )
        return []
    finally:
        if cur: cur.close()
        if conn: conn.close()

def get_monthly_financial_data_by_startup(startup_name: str):
    """Helper function to retrieve monthly iterations of financial data"""
    conn, cur = None, None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(f"""
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
            WHERE startup_name = %s
            ORDER BY date ASC
        """, (startup_name,))
        rows = cur.fetchall()

        if not rows:
            log_error("No monthly_financial_data found in DB")
            return []

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

    except Exception as e:
        log_error(
        error_type="DB_ERROR",
        error_message=f"Error in get_monthly_financial_data: {str(e)}",
        context={"function": "get_monthly_financial_data"}
    )
        return []

    finally:
        if cur: cur.close()
        if conn: conn.close()

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
        churned_customers = prev_active + new_customers - current_active
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
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
    current_cash = onboarding['initial_cash']
    
    for month in monthly_data:
        total_expenses = (month['product_dev_expenses'] + 
                         month['manpower_expenses'] + 
                         month['marketing_expenses'] + 
                         month['operations_expenses'] + 
                         month['other_expenses'])
        
        monthly_cash_flow = month['revenue'] - total_expenses
        current_cash += monthly_cash_flow
    
    return current_cash, len(monthly_data)

def get_current_metrics():
    """Helper function to get current financial state"""
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    current_cash, months_elapsed = calculate_current_cash()
    
    if monthly_data:
        latest = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
        avg_revenue = sum(month['revenue'] for month in latest) / len(latest)
        avg_expenses = sum(
            month['product_dev_expenses'] + month['manpower_expenses'] + 
            month['marketing_expenses'] + month['operations_expenses'] + month['other_expenses']
            for month in latest
        ) / len(latest)
        avg_marketing = sum(month['marketing_expenses'] for month in latest) / len(latest)
        avg_new_customers = sum(month['new_customers'] for month in latest) / len(latest)
    else:
        avg_revenue = onboarding['target_revenue']
        avg_expenses = (onboarding['planned_product_dev'] + onboarding['planned_manpower'] + 
                       onboarding['planned_marketing'] + onboarding['planned_operations'])
        avg_marketing = onboarding['planned_marketing']
        avg_new_customers = 0
    
    return {
        'current_cash': current_cash,
        'avg_revenue': avg_revenue,
        'avg_expenses': avg_expenses,
        'avg_marketing': avg_marketing,
        'avg_new_customers': avg_new_customers,
        'months_elapsed': months_elapsed
    }

@tool
def get_financial_summary():
    """Retrieve complete financial journey from onboarding to current state"""
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
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
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
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
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
    planned_burn = (onboarding['planned_product_dev'] + onboarding['planned_manpower'] + 
                   onboarding['planned_marketing'] + onboarding['planned_operations'])
    
    if not monthly_data:
        return f"Planned monthly burn rate: ₱{planned_burn:,.2f}\n(No actual data available yet)"
    
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    
    actual_burns = []
    revenues = []
    expense_breakdown = {'product_dev': [], 'manpower': [], 'marketing': [], 'operations': [], 'other': []}
    
    for month in recent_months:
        total_expenses = (month['product_dev_expenses'] + month['manpower_expenses'] + 
                         month['marketing_expenses'] + month['operations_expenses'] + month['other_expenses'])
        actual_burns.append(total_expenses)
        revenues.append(month['revenue'])
        
        expense_breakdown['product_dev'].append(month['product_dev_expenses'])
        expense_breakdown['manpower'].append(month['manpower_expenses'])
        expense_breakdown['marketing'].append(month['marketing_expenses'])
        expense_breakdown['operations'].append(month['operations_expenses'])
        expense_breakdown['other'].append(month['other_expenses'])
    
    avg_actual_burn = sum(actual_burns) / len(actual_burns)
    avg_revenue = sum(revenues) / len(revenues)
    net_burn = avg_actual_burn - avg_revenue
    
    # Calculate expense breakdown percentages
    breakdown_text = "\n\nEXPENSE BREAKDOWN (recent average):"
    for category, expenses in expense_breakdown.items():
        avg_expense = sum(expenses) / len(expenses)
        percentage = (avg_expense / avg_actual_burn * 100) if avg_actual_burn > 0 else 0
        breakdown_text += f"\n- {category.replace('_', ' ').title()}: ₱{avg_expense:,.2f} ({percentage:.1f}%)"
    
    return f"""BURN RATE ANALYSIS ({len(recent_months)}-month average):
- Planned burn rate: ₱{planned_burn:,.2f}/month
- Actual burn rate: ₱{avg_actual_burn:,.2f}/month
- Average revenue: ₱{avg_revenue:,.2f}/month
- Net burn rate: ₱{net_burn:,.2f}/month
- Variance from plan: ₱{avg_actual_burn - planned_burn:+,.2f}/month ({((avg_actual_burn - planned_burn) / planned_burn * 100):+.1f}%){breakdown_text}"""

@tool
def compute_runway(simulated_expense=None, simulated_revenue=None):
    """Compute current runway based on actual cash position and burn rate scenarios"""
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    current_cash, months_elapsed = calculate_current_cash()
    
    if simulated_expense is not None or simulated_revenue is not None:
        # Use current metrics as baseline
        metrics = get_current_metrics()
        expense = simulated_expense if simulated_expense is not None else metrics['avg_expenses']
        revenue = simulated_revenue if simulated_revenue is not None else metrics['avg_revenue']
        net_burn = expense - revenue
        
        if net_burn <= 0:
            return f"Simulated scenario: Cash positive! Generating ₱{abs(net_burn):,.2f}/month in positive cash flow"
        
        runway = math.floor(current_cash / net_burn)
        return f"Simulated runway: {runway} months (₱{current_cash:,.2f} ÷ ₱{net_burn:,.2f}/month net burn)\nExpenses: ₱{expense:,.2f}/month, Revenue: ₱{revenue:,.2f}/month"
    
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
    
    # Runway health assessment
    runway_status = ""
    if runway >= 12:
        runway_status = "\n✅ HEALTHY RUNWAY: Strong financial position (12+ months)"
    elif runway >= 6:
        runway_status = "\n👍 ADEQUATE RUNWAY: Safe zone but start planning next milestone (6-12 months)"
    elif runway >= 3:
        runway_status = "\n⚠️ SHORT RUNWAY: Concerning - need immediate action (3-6 months)"
    else:
        runway_status = "\n🚨 CRITICAL RUNWAY: Dangerous situation - urgent funding needed (<3 months)"
    
    return f"""Current runway: {runway} months
- Current cash: ₱{current_cash:,.2f}
- Average monthly revenue: ₱{avg_revenue:,.2f}
- Average monthly expenses: ₱{avg_expenses:,.2f}
- Net monthly burn: ₱{net_burn:,.2f}
({len(recent_months)} month average){runway_status}"""

@tool
def compute_cac():
    """
    Compute the Customer Acquisition Cost (CAC) based on historical data.
    CAC = Total Marketing Expenses / New Customers Acquired (for a given period)
    """
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)

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

    # CAC health assessment
    health_assessment = "\n\nCAC HEALTH ASSESSMENT:"
    if recent_cac != float('inf'):
        if recent_cac < 500:
            health_assessment += "\n✅ EXCELLENT: Very efficient customer acquisition"
        elif recent_cac < 2000:
            health_assessment += "\n👍 GOOD: Reasonable customer acquisition cost"
        elif recent_cac < 5000:
            health_assessment += "\n⚠️ CONCERNING: High customer acquisition cost"
        else:
            health_assessment += "\n❌ CRITICAL: Very expensive customer acquisition"
    else:
        health_assessment += "\n❓ UNKNOWN: No recent customer acquisitions to analyze"

    return f"""CUSTOMER ACQUISITION COST (CAC) - {onboarding['startup_name']}

ACQUISITION METRICS:
- Lifetime CAC: {lifetime_cac_display}
- Recent CAC (last {len(recent_months)} months): {recent_cac_display}
- Lifetime marketing spend: ₱{total_marketing:,.2f}
- Lifetime new customers acquired: {total_new_customers}
- Recent marketing spend: ₱{recent_marketing:,.2f}
- Recent new customers: {recent_new_customers}{health_assessment}"""

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
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
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
    
    # Calculate payback period (CAC / monthly revenue per customer)
    payback_period = (recent_cac / arpu) if arpu > 0 and recent_cac != float('inf') else float('inf')
    
    ltv_display = f"₱{ltv:,.2f}" if ltv != float('inf') else "∞ (No churn detected)"
    lifespan_display = f"{customer_lifespan:.1f} months" if customer_lifespan != float('inf') else "∞ (No churn)"
    ratio_display = f"{ltv_cac_ratio:.1f}:1" if ltv_cac_ratio != float('inf') else "∞:1"
    recent_cac_display = f"₱{recent_cac:,.2f}" if recent_cac != float('inf') else "∞"
    payback_display = f"{payback_period:.1f} months" if payback_period != float('inf') else "∞"
    
    analysis = f"""CUSTOMER LIFETIME VALUE (LTV) - {onboarding['startup_name']}

LTV CALCULATION:
- Average Revenue Per Customer (ARPU): ₱{arpu:,.2f}/month
- Average Customer Lifespan: {lifespan_display}
- Customer Lifetime Value: {ltv_display}

UNIT ECONOMICS:
- LTV: {ltv_display}
- CAC: {recent_cac_display}
- LTV:CAC Ratio: {ratio_display}
- Payback Period: {payback_display}
- Recent marketing spend: ₱{recent_marketing:,.2f}
- Recent new customers: {recent_new_customers}

HEALTH ASSESSMENT:"""
    
    if ltv_cac_ratio >= 3:
        analysis += "\n✅ EXCELLENT: Strong LTV:CAC ratio (≥3:1)"
    elif ltv_cac_ratio >= 2:
        analysis += "\n👍 GOOD: Healthy unit economics (2-3:1)"
    elif ltv_cac_ratio >= 1:
        analysis += "\n⚠️ CONCERNING: Break-even unit economics (1-2:1)"
    else:
        analysis += "\n❌ CRITICAL: Negative unit economics (<1:1)"
    
    return analysis

import math
@tool
def analyze_hiring_affordability(role="developer", monthly_salary=None, num_hires=1):
    """Analyze if startup can afford to hire new employee(s) by recalculating runway.

    """
    startup_name = get_startup_name()
    if monthly_salary is None:
        raise ValueError(f"Monthly salary must be provided for {role} position.")

    monthly_data = get_monthly_financial_data(startup_name)
    current_cash, _ = calculate_current_cash()
    
    # Calculate current burn rate (3-month average if available)
    if monthly_data:
        recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
        avg_expenses = sum(
            m['product_dev_expenses'] + m['manpower_expenses'] +
            m['marketing_expenses'] + m['operations_expenses'] +
            m['other_expenses']
            for m in recent_months
        ) / len(recent_months)
        avg_revenue = sum(m['revenue'] for m in recent_months) / len(recent_months)
        net_burn = avg_expenses - avg_revenue
    else:
        onboarding = get_onboarding_data(startup_name)
        avg_expenses = (
            onboarding['planned_product_dev'] +
            onboarding['planned_manpower'] +
            onboarding['planned_marketing'] +
            onboarding['planned_operations']
        )
        avg_revenue = onboarding['target_revenue']
        net_burn = avg_expenses - avg_revenue

    current_runway = math.floor(current_cash / net_burn) if net_burn > 0 else float('inf')
    
    # Add new hires to monthly expenses
    total_new_salary = monthly_salary * num_hires
    new_monthly_expenses = avg_expenses + total_new_salary
    new_net_burn = new_monthly_expenses - avg_revenue
    new_runway = math.floor(current_cash / new_net_burn) if new_net_burn > 0 else float('inf')
    runway_impact = new_runway - current_runway if current_runway != float('inf') else 0
    
    hire_text = f"{num_hires} {role}{'s' if num_hires > 1 else ''}"
    
    analysis = f"""HIRING AFFORDABILITY ANALYSIS - {hire_text.title()}:

SALARY IMPACT:
- Salary per hire: ₱{monthly_salary:,.2f}/month
- Total new salary cost: ₱{total_new_salary:,.2f}/month
- Number of hires: {num_hires}

COMPUTATIONS:
- Current monthly expenses: ₱{avg_expenses:,.2f}/month
- New monthly expenses (including hire(s)): ₱{new_monthly_expenses:,.2f}/month
- Current net burn rate: ₱{net_burn:,.2f}/month
- New net burn rate: ₱{new_net_burn:,.2f}/month

RUNWAY IMPACT:
- Current runway: {current_runway if current_runway != float('inf') else '∞'} months
- New runway with hire(s): {new_runway if new_runway != float('inf') else '∞'} months
- Runway impact: {runway_impact:+} months
"""

    # Simple affordability assessment
    if new_runway < 3:
        analysis += "\n🚨 CRITICAL: Runway <3 months. Hiring not recommended."
    elif new_runway < 6:
        analysis += "\n❌ DANGEROUS: Short runway (3-6 months). Hire only if revenue growth expected."
    elif new_runway < 12:
        analysis += "\n⚠️ RISKY: Runway 6-12 months. Consider timing and fundraising."
    else:
        analysis += "\n✅ AFFORDABLE: Healthy runway (12+ months) and strong cash position."
    
    return analysis

@tool
def scenario_planning(revenue_change_pct=0, expense_change_pct=0, marketing_change_pct=0, marketing_change_amount=0, months_to_project=12):
    """Run scenario planning with revenue and expense changes. Perfect for 'what if' questions like:
    - 'What happens to runway if revenue drops by 20%?' → revenue_change_pct=-20
    - 'If we cut expenses by 15%?' → expense_change_pct=-15
    - 'If we increase marketing spend by 50%?' → marketing_change_pct=50
    - 'What if I cut marketing costs by ₱100,000?' → marketing_change_amount=-100000

    """
    metrics = get_current_metrics()
    startup_name = get_startup_name()
    
    # Calculate scenario values
    current_revenue = metrics['avg_revenue']
    current_expenses = metrics['avg_expenses']
    current_marketing = metrics['avg_marketing']
    current_net_burn = current_expenses - current_revenue
    current_runway = math.floor(metrics['current_cash'] / current_net_burn) if current_net_burn > 0 else float('inf')
    
    new_revenue = current_revenue * (1 + revenue_change_pct / 100)
    
    # Handle marketing changes - prioritize absolute amount over percentage
    if marketing_change_amount != 0:
        new_marketing = current_marketing + marketing_change_amount
        marketing_adjustment = marketing_change_amount
    else:
        marketing_adjustment = current_marketing * (marketing_change_pct / 100)
        new_marketing = current_marketing + marketing_adjustment
    
    # Ensure marketing doesn't go negative
    new_marketing = max(0, new_marketing)
    actual_marketing_adjustment = new_marketing - current_marketing
    
    # Apply expense changes
    base_expenses = current_expenses
    # First apply the marketing-specific change, then apply overall expense percentage change
    adjusted_expenses = base_expenses + actual_marketing_adjustment
    new_expenses = adjusted_expenses * (1 + expense_change_pct / 100)
    
    new_net_burn = new_expenses - new_revenue
    
    # Handle scenario where net burn is zero or negative (cash positive)
    if new_net_burn <= 0:
        runway = float('inf')
        cash_out_month = None
    else:
        # Project forward only if burning cash
        runway = math.floor(metrics['current_cash'] / new_net_burn)
        cash_out_month = runway + 1 if runway < months_to_project else None
    
    # Create simplified projections for milestones
    monthly_projections = []
    projected_cash = metrics['current_cash']
    
    if new_net_burn > 0:  # Only create projections if burning cash
        for month in range(1, min(months_to_project + 1, runway + 2)):
            projected_cash -= new_net_burn
            monthly_projections.append({
                'month': month,
                'cash': projected_cash,
                'revenue': new_revenue,
                'expenses': new_expenses,
                'marketing': new_marketing,
                'net_burn': new_net_burn
            })
            
            if projected_cash <= 0:
                break

    scenario_name = []
    if revenue_change_pct != 0:
        scenario_name.append(f"Revenue {revenue_change_pct:+.0f}%")
    if expense_change_pct != 0:
        scenario_name.append(f"Expenses {expense_change_pct:+.0f}%")
    if marketing_change_amount != 0:
        scenario_name.append(f"Marketing {actual_marketing_adjustment:+,.0f}")
    elif marketing_change_pct != 0:
        scenario_name.append(f"Marketing {marketing_change_pct:+.0f}%")
    
    scenario_title = " + ".join(scenario_name) if scenario_name else "Current Trajectory"
    
    # Calculate runway impact safely
    if current_runway != float('inf'):
        runway_change = runway - current_runway
        runway_change_text = f"{runway_change:+} months"
        runway_comparison = f"{current_runway} → {runway}"
    else:
        runway_change_text = "N/A (was infinite)"
        runway_comparison = f"∞ → {runway}"

    analysis = f"""SCENARIO PLANNING - {scenario_title}

CURRENT STATE:
- Current Cash: ₱{metrics['current_cash']:,.2f}
- Current Revenue: ₱{current_revenue:,.2f}/month
- Current Expenses: ₱{current_expenses:,.2f}/month
- Current Marketing: ₱{current_marketing:,.2f}/month
- Current Net Burn: ₱{current_net_burn:,.2f}/month
- Current Runway: {current_runway if current_runway != float('inf') else '∞'} months

SCENARIO ASSUMPTIONS:
- New Revenue: ₱{new_revenue:,.2f}/month ({revenue_change_pct:+.1f}% change)
- New Marketing: ₱{new_marketing:,.2f}/month ({actual_marketing_adjustment:+,.0f} change)
- New Total Expenses: ₱{new_expenses:,.2f}/month
- New Net Burn: ₱{new_net_burn:,.2f}/month

IMPACT ANALYSIS:
- Runway Change: {runway_change_text} ({runway_comparison})
- Cash runs out: {'Month ' + str(cash_out_month) if cash_out_month else 'Beyond projection period'}

CAC IMPACT ANALYSIS:"""

    # Calculate CAC impact if we have customer data
    monthly_data = get_monthly_financial_data(startup_name)
    if monthly_data and new_marketing != current_marketing:
        recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
        recent_new_customers = sum(month['new_customers'] for month in recent_months) / len(recent_months)
        
        if recent_new_customers > 0:
            current_cac = current_marketing / recent_new_customers
            new_cac = new_marketing / recent_new_customers  # Assuming same acquisition rate
            cac_change = new_cac - current_cac
            cac_change_pct = (cac_change / current_cac * 100) if current_cac > 0 else 0
            
            analysis += f"""
- Current CAC: ₱{current_cac:,.2f}
- New CAC: ₱{new_cac:,.2f} (assuming same acquisition rate)
- CAC Change: ₱{cac_change:+,.2f} ({cac_change_pct:+.1f}%)
- Monthly new customers: {recent_new_customers:.0f} (current rate)"""

    analysis += "\n\nRUNWAY ASSESSMENT:"
    # Runway health assessment for the scenario
    if new_net_burn <= 0:
        analysis += "\n🎉 CASH POSITIVE: No runway concerns - generating positive cash flow!"
    elif runway >= 12:
        analysis += "\n✅ HEALTHY: Strong runway even in this scenario (12+ months)"
    elif runway >= 6:
        analysis += "\n👍 ADEQUATE: Manageable runway in this scenario (6-12 months)"  
    elif runway >= 3:
        analysis += "\n⚠️ SHORT: Concerning runway in this scenario (3-6 months)"
    else:
        analysis += "\n🚨 CRITICAL: Dangerous runway in this scenario (<3 months)"
    
    # Show milestones only if we have projections
    if monthly_projections:
        milestones = [3, 6, 12, 18, 24]
        analysis += "\n\nCASH MILESTONES:"
        for milestone in milestones:
            if milestone <= len(monthly_projections):
                cash_at_milestone = monthly_projections[milestone-1]['cash']
                analysis += f"\n- Month {milestone}: ₱{cash_at_milestone:,.2f}"
            elif milestone <= months_to_project and new_net_burn > 0:
                analysis += f"\n- Month {milestone}: Cash depleted"
    
    # Breakeven analysis
    if new_net_burn <= 0:
        analysis += f"\n\n🎉 BREAKEVEN ACHIEVED! Positive cash flow of ₱{abs(new_net_burn):,.2f}/month"
    else:
        breakeven_revenue_needed = new_expenses
        revenue_gap = breakeven_revenue_needed - new_revenue
        analysis += f"\n\nBREAKEVEN ANALYSIS:"
        analysis += f"\n- Revenue needed for breakeven: ₱{breakeven_revenue_needed:,.2f}/month"
        analysis += f"\n- Current revenue gap: ₱{revenue_gap:,.2f}/month"
        analysis += f"\n- Required revenue growth: {(revenue_gap / new_revenue * 100):+.1f}%"
    
    return analysis

@tool
def fundraising_analysis(raise_amount=None, target_runway_months=18, current_valuation=None):
    """Analyze fundraising scenarios and requirements
    
    Args:
        raise_amount: Amount to raise (if None, calculates minimum needed)
        target_runway_months: Desired runway after fundraising
        current_valuation: Current company valuation for dilution calculation
    """
    metrics = get_current_metrics()
    current_net_burn = metrics['avg_expenses'] - metrics['avg_revenue']
    
    if raise_amount is None:
        # Calculate minimum raise needed
        cash_needed = current_net_burn * target_runway_months
        buffer_needed = cash_needed * 0.2  # 20% buffer
        raise_amount = cash_needed + buffer_needed - metrics['current_cash']
        raise_amount = max(0, raise_amount)  # Don't go negative
    
    new_cash = metrics['current_cash'] + raise_amount
    new_runway = math.floor(new_cash / current_net_burn) if current_net_burn > 0 else float('inf')
    
    # Calculate dilution if valuation provided
    dilution_text = ""
    if current_valuation is not None and current_valuation > 0:
        post_money_valuation = current_valuation + raise_amount
        dilution_pct = (raise_amount / post_money_valuation) * 100
        dilution_text = f"""
DILUTION ANALYSIS:
- Pre-money valuation: ₱{current_valuation:,.2f}
- Post-money valuation: ₱{post_money_valuation:,.2f}
- Dilution: {dilution_pct:.1f}%"""
    
    # Series recommendations based on raise size
    if raise_amount < 5_000_000:
        series_rec = "Pre-Seed/Angel"
    elif raise_amount < 25_000_000:
        series_rec = "Seed Round"
    elif raise_amount < 100_000_000:
        series_rec = "Series A"
    else:
        series_rec = "Series B+"
    
    analysis = f"""FUNDRAISING ANALYSIS

CURRENT FINANCIAL STATE:
- Current cash: ₱{metrics['current_cash']:,.2f}
- Monthly net burn: ₱{current_net_burn:,.2f}
- Current runway: {math.floor(metrics['current_cash'] / current_net_burn) if current_net_burn > 0 else '∞'} months

FUNDRAISING SCENARIO:
- Raise amount: ₱{raise_amount:,.2f}
- New total cash: ₱{new_cash:,.2f}
- New runway: {new_runway if new_runway != float('inf') else '∞'} months
- Recommended round type: {series_rec}{dilution_text}

FUNDRAISING READINESS:"""
    
    # Assess fundraising readiness
    if new_runway >= 18:
        analysis += "\n✅ OPTIMAL: Excellent runway for growth and next milestone"
    elif new_runway >= 12:
        analysis += "\n👍 GOOD: Adequate runway, consider market timing"
    elif new_runway >= 6:
        analysis += "\n⚠️ MINIMUM: Just enough runway, raise more if possible"
    else:
        analysis += "\n❌ INSUFFICIENT: Need to raise more for adequate runway"
    
    # Calculate different raise scenarios
    analysis += "\n\nRAISE SCENARIOS:"
    scenarios = [raise_amount * 0.5, raise_amount, raise_amount * 1.5]
    for i, amount in enumerate(scenarios):
        scenario_cash = metrics['current_cash'] + amount
        scenario_runway = math.floor(scenario_cash / current_net_burn) if current_net_burn > 0 else float('inf')
        scenario_names = ["Conservative", "Target", "Aggressive"]
        analysis += f"\n- {scenario_names[i]}: ₱{amount:,.2f} → {scenario_runway if scenario_runway != float('inf') else '∞'} months runway"
    
    return analysis

@tool
def marketing_scaling_analysis(cac_target=None, budget_increase_pct=0, efficiency_change_pct=0):
    """Analyze marketing scaling opportunities and CAC optimization
    
    Args:
        cac_target: Target CAC to achieve (if None, uses current CAC)
        budget_increase_pct: Percentage increase in marketing budget
        efficiency_change_pct: Percentage change in marketing efficiency (negative = worse, positive = better)
    """
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
    if not monthly_data:
        return "No monthly financial data available for marketing analysis."
    
    # Get current metrics
    recent_cac, recent_marketing, recent_new_customers = calculate_cac_helper(monthly_data, 3)
    current_cac = recent_cac if recent_cac != float('inf') else 0
    
    # Calculate LTV for comparison
    churn_data = calculate_customer_churn(monthly_data, onboarding)
    if churn_data:
        recent_churn_data = churn_data[-3:] if len(churn_data) >= 3 else churn_data
        recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
        
        avg_revenue = sum(month['revenue'] for month in recent_months) / len(recent_months)
        avg_active_customers = sum(month['active_customers'] for month in recent_months) / len(recent_months)
        arpu = avg_revenue / avg_active_customers if avg_active_customers > 0 else 0
        
        avg_monthly_churn_rate = sum(month['churn_rate'] for month in recent_churn_data) / len(recent_churn_data) / 100
        customer_lifespan = (1 / avg_monthly_churn_rate) if avg_monthly_churn_rate > 0 else float('inf')
        ltv = arpu * customer_lifespan if customer_lifespan != float('inf') else float('inf')
    else:
        ltv = float('inf')
        arpu = 0
    
    # Calculate new marketing scenario
    new_marketing_budget = recent_marketing * (1 + budget_increase_pct / 100)
    marketing_efficiency_multiplier = 1 + (efficiency_change_pct / 100)
    
    # New customers acquired with efficiency changes
    baseline_customers_per_peso = recent_new_customers / recent_marketing if recent_marketing > 0 else 0
    new_customers_per_peso = baseline_customers_per_peso * marketing_efficiency_multiplier
    projected_new_customers = new_marketing_budget * new_customers_per_peso
    
    projected_cac = new_marketing_budget / projected_new_customers if projected_new_customers > 0 else float('inf')
    
    # LTV:CAC analysis
    ltv_cac_ratio = ltv / projected_cac if projected_cac != float('inf') and projected_cac > 0 and ltv != float('inf') else float('inf')
    
    # Format display values to avoid f-string issues
    ltv_display = f"₱{ltv:,.2f}" if ltv != float('inf') else "∞"
    
    # Safe current LTV:CAC calculation
    if current_cac > 0 and ltv != float('inf'):
        current_ltv_cac_ratio = ltv / current_cac
        current_ltv_cac_display = f"{current_ltv_cac_ratio:.1f}:1"
    else:
        current_ltv_cac_display = "∞:1"
    
    projected_cac_display = f"₱{projected_cac:,.2f}" if projected_cac != float('inf') else "∞"
    projected_ltv_cac_display = f"{ltv_cac_ratio:.1f}:1" if ltv_cac_ratio != float('inf') else "∞:1"
    
    analysis = f"""MARKETING SCALING ANALYSIS

CURRENT PERFORMANCE:
- Current marketing spend: ₱{recent_marketing:,.2f}/month
- Current new customers: {recent_new_customers}/month
- Current CAC: ₱{current_cac:,.2f}
- Customer LTV: {ltv_display}
- Current LTV:CAC: {current_ltv_cac_display}

SCALING SCENARIO:
- New marketing budget: ₱{new_marketing_budget:,.2f}/month ({budget_increase_pct:+.1f}% change)
- Marketing efficiency change: {efficiency_change_pct:+.1f}%
- Projected new customers: {projected_new_customers:.0f}/month
- Projected CAC: {projected_cac_display}
- Projected LTV:CAC: {projected_ltv_cac_display}

SCALING ASSESSMENT:"""
    
    if projected_cac != float('inf') and ltv != float('inf'):
        if ltv_cac_ratio >= 3:
            analysis += "\n✅ EXCELLENT: Strong unit economics, scale aggressively"
        elif ltv_cac_ratio >= 2:
            analysis += "\n👍 GOOD: Healthy scaling opportunity"
        elif ltv_cac_ratio >= 1:
            analysis += "\n⚠️ BREAK-EVEN: Scaling will not hurt but won't help profitability"
        else:
            analysis += "\n❌ UNPROFITABLE: Scaling will worsen unit economics"
    
    # Budget recommendations
    max_profitable_cac = ltv / 3 if ltv != float('inf') else float('inf')  # Conservative 3:1 ratio
    max_monthly_marketing = max_profitable_cac * projected_new_customers if max_profitable_cac != float('inf') else float('inf')
    
    analysis += f"\n\nRECOMMENDATIONS:"
    analysis += f"\n- Maximum profitable CAC: ₱{max_profitable_cac:,.2f if max_profitable_cac != float('inf') else '∞'}"
    analysis += f"\n- Maximum recommended marketing spend: ₱{max_monthly_marketing:,.2f if max_monthly_marketing != float('inf') else '∞'}/month"
    
    # Show payback period
    if arpu > 0 and projected_cac != float('inf'):
        payback_months = projected_cac / arpu
        analysis += f"\n- Customer payback period: {payback_months:.1f} months"
    
    return analysis
@tool
def expense_optimization_analysis():
    """Analyze expense categories and identify optimization opportunities"""
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
    if not monthly_data:
        return "No monthly financial data available for expense analysis."
    
    # Calculate recent averages
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    
    expense_categories = {
        'Product Development': sum(m['product_dev_expenses'] for m in recent_months) / len(recent_months),
        'Manpower': sum(m['manpower_expenses'] for m in recent_months) / len(recent_months),
        'Marketing': sum(m['marketing_expenses'] for m in recent_months) / len(recent_months),
        'Operations': sum(m['operations_expenses'] for m in recent_months) / len(recent_months),
        'Other': sum(m['other_expenses'] for m in recent_months) / len(recent_months)
    }
    
    total_expenses = sum(expense_categories.values())
    
    # Compare with planned expenses
    planned_expenses = {
        'Product Development': onboarding['planned_product_dev'],
        'Manpower': onboarding['planned_manpower'],
        'Marketing': onboarding['planned_marketing'],
        'Operations': onboarding['planned_operations']
    }
    
    analysis = f"""EXPENSE OPTIMIZATION ANALYSIS - {len(recent_months)}-month average

EXPENSE BREAKDOWN:
- Total Monthly Expenses: ₱{total_expenses:,.2f}"""
    
    # Sort categories by size for analysis
    sorted_expenses = sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)
    
    for category, amount in sorted_expenses:
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        planned = planned_expenses.get(category, 0)
        variance = amount - planned if planned > 0 else 0
        variance_pct = (variance / planned * 100) if planned > 0 else 0
        
        analysis += f"\n- {category}: ₱{amount:,.2f} ({percentage:.1f}%)"
        if planned > 0:
            analysis += f" [vs ₱{planned:,.2f} planned, {variance_pct:+.1f}%]"
    
    # Optimization recommendations
    analysis += "\n\nOPTIMIZATION OPPORTUNITIES:"
    
    largest_category = sorted_expenses[0]
    if largest_category[1] > total_expenses * 0.4:  # If any category is >40%
        analysis += f"\n🎯 PRIORITY: {largest_category[0]} represents {(largest_category[1]/total_expenses*100):.1f}% of expenses"
    
    # Identify categories over plan
    over_budget = [(cat, amt, planned_expenses.get(cat, 0)) for cat, amt in expense_categories.items() 
                   if planned_expenses.get(cat, 0) > 0 and amt > planned_expenses.get(cat, 0) * 1.1]
    
    if over_budget:
        analysis += "\n⚠️ OVER BUDGET:"
        for category, actual, planned in over_budget:
            overage = actual - planned
            overage_pct = (overage / planned * 100)
            analysis += f"\n- {category}: +₱{overage:,.2f} (+{overage_pct:.1f}%) over plan"
    
    # Calculate potential savings scenarios
    analysis += "\n\nSAVINGS SCENARIOS:"
    savings_scenarios = [5, 10, 20]  # percentage cuts
    
    for cut_pct in savings_scenarios:
        savings = total_expenses * (cut_pct / 100)
        new_total = total_expenses - savings
        
        # Calculate runway impact
        metrics = get_current_metrics()
        current_net_burn = metrics['avg_expenses'] - metrics['avg_revenue']
        new_net_burn = new_total - metrics['avg_revenue']
        
        current_runway = math.floor(metrics['current_cash'] / current_net_burn) if current_net_burn > 0 else float('inf')
        new_runway = math.floor(metrics['current_cash'] / new_net_burn) if new_net_burn > 0 else float('inf')
        runway_extension = new_runway - current_runway if current_runway != float('inf') else 0
        
        analysis += f"\n- {cut_pct}% cut: Save ₱{savings:,.2f}/month, extend runway by {runway_extension:+} months"
    
    return analysis

@tool
def analyze_churn_impact(hypothetical_monthly_churn_rate):
    """Analyze how a specific churn rate affects payback period, LTV, and unit economics.
    
    Args:
        hypothetical_monthly_churn_rate: Monthly churn rate as percentage (e.g., 5 for 5%)
    """
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
    if not monthly_data:
        return "No monthly financial data available for churn impact analysis."
    
    # Get current metrics
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    avg_revenue = sum(month['revenue'] for month in recent_months) / len(recent_months)
    avg_active_customers = sum(month['active_customers'] for month in recent_months) / len(recent_months)
    
    # Calculate ARPU (Average Revenue Per User per month)
    arpu = avg_revenue / avg_active_customers if avg_active_customers > 0 else 0
    
    # Calculate current CAC manually (don't use helper function)
    recent_marketing = sum(month['marketing_expenses'] for month in recent_months) / len(recent_months)
    recent_new_customers = sum(month['new_customers'] for month in recent_months) / len(recent_months)
    current_cac = recent_marketing / recent_new_customers if recent_new_customers > 0 else float('inf')
    
    # Get current churn for comparison
    churn_data = calculate_customer_churn(monthly_data, onboarding)
    if churn_data:
        recent_churn_data = churn_data[-3:] if len(churn_data) >= 3 else churn_data
        current_avg_churn_rate = sum(month['churn_rate'] for month in recent_churn_data) / len(recent_churn_data)
    else:
        current_avg_churn_rate = 0
    
    # Calculate metrics with hypothetical churn rate
    hypothetical_churn_decimal = hypothetical_monthly_churn_rate / 100
    
    # Customer lifespan = 1 / monthly churn rate
    customer_lifespan_months = 1 / hypothetical_churn_decimal if hypothetical_churn_decimal > 0 else float('inf')
    
    # LTV = ARPU × Customer Lifespan
    ltv = arpu * customer_lifespan_months if customer_lifespan_months != float('inf') else float('inf')
    
    # Payback period = CAC / ARPU (months to recover acquisition cost)
    payback_period = current_cac / arpu if arpu > 0 and current_cac != float('inf') else float('inf')
    
    # LTV:CAC ratio
    ltv_cac_ratio = ltv / current_cac if current_cac != float('inf') and current_cac > 0 and ltv != float('inf') else float('inf')
    
    # Format display values
    ltv_display = f"₱{ltv:,.2f}" if ltv != float('inf') else "∞"
    lifespan_display = f"{customer_lifespan_months:.1f} months" if customer_lifespan_months != float('inf') else "∞"
    payback_display = f"{payback_period:.1f} months" if payback_period != float('inf') else "∞"
    ratio_display = f"{ltv_cac_ratio:.1f}:1" if ltv_cac_ratio != float('inf') else "∞:1"
    current_cac_display = f"₱{current_cac:,.2f}" if current_cac != float('inf') else "∞"
    
    analysis = f"""CHURN IMPACT ANALYSIS - {hypothetical_monthly_churn_rate}% Monthly Churn

SCENARIO RESULTS:
- Monthly churn rate: {hypothetical_monthly_churn_rate}%
- Customer lifespan: {lifespan_display}
- Customer LTV: {ltv_display}
- Payback period: {payback_display}
- LTV:CAC ratio: {ratio_display}

BASELINE METRICS:
- Current monthly churn: {current_avg_churn_rate:.1f}%
- ARPU: ₱{arpu:,.2f}/month
- CAC: {current_cac_display}

KEY INSIGHT: Payback period remains {payback_display} regardless of churn rate.
LTV changes significantly: at {hypothetical_monthly_churn_rate}% churn, each customer generates {ltv_display} over their lifetime."""

    # Health assessment
    if hypothetical_monthly_churn_rate <= 5:
        analysis += "\n\n✅ HEALTHY churn rate for most businesses"
    elif hypothetical_monthly_churn_rate <= 10:
        analysis += "\n\n⚠️ MODERATE churn rate - monitor retention"
    else:
        analysis += "\n\n❌ HIGH churn rate - focus on retention immediately"

    return analysis


@tool
def churn_scenario_comparison(churn_rates_list=[2, 5, 10, 15, 20]):
    """Compare multiple churn rate scenarios side by side.
    
    Args:
        churn_rates_list: List of monthly churn rates to compare (as percentages)
    """
    startup_name = get_startup_name()
    onboarding = get_onboarding_data(startup_name)
    monthly_data = get_monthly_financial_data(startup_name)
    
    if not monthly_data:
        return "No monthly financial data available for churn scenario comparison."
    
    # Get current metrics
    recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
    avg_revenue = sum(month['revenue'] for month in recent_months) / len(recent_months)
    avg_active_customers = sum(month['active_customers'] for month in recent_months) / len(recent_months)
    arpu = avg_revenue / avg_active_customers if avg_active_customers > 0 else 0
    
    recent_cac, recent_marketing, recent_new_customers = calculate_cac_helper(monthly_data, 3)
    
    analysis = f"""CHURN SCENARIO COMPARISON

BASELINE METRICS:
- ARPU: ₱{arpu:,.2f}/month
- CAC: ₱{recent_cac:,.2f if recent_cac != float('inf') else '∞'}

SCENARIOS:"""
    
    for churn_rate in churn_rates_list:
        churn_decimal = churn_rate / 100
        lifespan = 1 / churn_decimal if churn_decimal > 0 else float('inf')
        ltv = arpu * lifespan if lifespan != float('inf') else float('inf')
        payback = recent_cac / arpu if arpu > 0 and recent_cac != float('inf') else float('inf')
        ltv_cac = ltv / recent_cac if ltv != float('inf') and recent_cac != float('inf') and recent_cac > 0 else float('inf')
        
        ltv_display = f"₱{ltv:,.2f}" if ltv != float('inf') else "∞"
        payback_display = f"{payback:.1f}mo" if payback != float('inf') else "∞"
        ratio_display = f"{ltv_cac:.1f}:1" if ltv_cac != float('inf') else "∞:1"
        
        analysis += f"\n{churn_rate:2.0f}% churn: {lifespan:4.1f}mo lifespan → LTV {ltv_display:>12} → Payback {payback_display:>6} → Ratio {ratio_display:>6}"
    
    analysis += f"\n\nKEY INSIGHTS:"
    analysis += f"\n- Payback period is constant at {payback:.1f} months (independent of churn)"
    analysis += f"\n- LTV increases dramatically as churn decreases"
    analysis += f"\n- Each 1% reduction in churn extends customer lifespan significantly"
    
    return analysis

# Add the new tools to the tools list
tools = [
    get_financial_summary, 
    analyze_customer_churn, 
    compute_burn_rate, 
    compute_runway,
    compute_cac,
    compute_customer_ltv,
    analyze_hiring_affordability,
    scenario_planning,
    fundraising_analysis,
    marketing_scaling_analysis,
    expense_optimization_analysis,
    analyze_churn_impact,
    churn_scenario_comparison
]