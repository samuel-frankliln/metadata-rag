# Metadata: sample_customers.csv

| Column | Type | Description | Example Values | Business Rules | Quality Notes |
|--------|------|-------------|----------------|----------------|---------------|
| `customer_id` | identifier | Unique identifier assigned to each customer at registration. | C001, C002, C003 | Never reused after account deletion. | null identified |
| `first_name` | string | Customer's legal name as provided at signup. | Alice, Bob, Carmen | Not validated against government ID. May contain Unicode characters for international customers. | null identified |
| `last_name` | string | Customer's legal name as provided at signup. | Johnson, Smith, Rodriguez | Not validated against government ID. May contain Unicode characters for international customers. | null identified |
| `email` | string | Primary contact email used for login and notifications. | alice.j@email.com, bob.smith@email.com | Must be unique across all accounts. Some enterprise accounts may have no email if SSO is configured (nullable). | Email is nullable for enterprise SSO accounts (about 2% of accounts) |
| `phone` | string | International format with country code used for 2FA and support contact. | +1-555-0101, +34-600-123456 | Format varies by country. Not guaranteed to be unique (family plans may share a number). | Phone numbers are not standardized — some include dashes, spaces, or parentheses |
| `date_of_birth` | datetime | Customer's date of birth. | 1985-03-12, 1990-07-24 | null identified | null identified |
| `signup_date` | datetime | Date of customer's signup. | 2021-06-15, 2022-01-03 | null identified | null identified |
| `country` | string | Customer's country of residence. | USA, Spain | Country field was added in 2020; records before that may have NULL country | null identified |
| `subscription_plan` | string | Customer's subscription plan. | premium, basic | null identified | null identified |
| `monthly_spend` | decimal | Actual billed amount in USD for the current billing cycle. | 149.99, 9.99 | May differ from plan price due to add-ons, discounts, or proration. Enterprise customers may have custom pricing — treat as sensitive financial data. | null identified |
| `is_active` | boolean | Indicates whether the customer's account is active. | True, False | null identified | null identified |
| `last_login` | datetime | Date of the customer's last login. | 2024-11-01, 2024-07-22 | null identified | null identified |