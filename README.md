# Cashflow-Guardian
Repository for our BPI DataWave Product

### Setup Instructions
- gawa kayo venv nyo tas run "pip install -r requirements.txt" para ma-dl lahat ng need na libraries
- then sa database (Postgre) gawa kayo onboarding_data at monthly_financial_data na tables
- to run backend: cd to app folder, then run uvicorn main:api --reload -port 8000 in the terminal
### onboarding_data column names:
- startup_name
- industry
- target_revenue
- product_dev_expenses
- manpower_expenses
- marketing_expenses
- operations_expenses
- initial_cash
- initial_customers
- current_employees
- target_runway_months
- onboarding_date

### monthly_financial_data column names:
- date
- revenue
- product_dev_expenses
- manpower_expenses
- marketing_expenses
- operations_expenses
- new_customers
- active_customers
- other_expenses

### .env variable names:
- GOOGLE_API_KEY
- DB_USERNAME
- DB_PASSWORD
- DB_PORT
- DB_HOST
- DB_NAME

            
            
            
