# cc

### Banks list

HDFC Bank
State Bank of India (SBI Card)
ICICI Bank
Axis Bank
Kotak Mahindra Bank
IndusInd Bank
RBL Bank
IDFC FIRST Bank
Federal Bank
YES Bank
AU Small Finance Bank
Standard Chartered Bank
HSBC India
American Express
Bank of Baroda
Canara Bank
Union Bank of India
Punjab National Bank
Indian Bank
Bank of India

### DATA EXTRACTION FIELDS

**1) Card master data**

```
card_id
card_name
bank_id
card_type (credit/debit)
card_network (Visa/Mastercard/RuPay/Amex)
variant/tier (classic/platinum/signature/infinite/etc.)
card_category (cashback/travel/fuel/entry-level/student/luxury/etc.)
official_url
status (active/discontinued)
launch_date
last_verified_at
```

**2) Pricing / fees**

```
joining_fee
annual_fee
annual_fee_waiver_condition
late_payment_fee
cash_withdrawal_fee
forex_markup
cashback_cap_fee
reward_redemption_fee
add_on_card_fee
```

**3) Benefit engine data**

```
reward_type (points/cashback/miles)
reward_rate_general
reward_rate_category_wise
bonus_categories
welcome_bonus
milestone_bonuses
fuel_surcharge_waiver
lounge_access
airport_meet_greet
movie_offer
dining_offer
grocery_offer
travel_benefits
insurance_benefits
EMI_conversions
contactless/UPI/support
```

**4) Eligibility + approval likelihood**

```
minimum_income
employment_type
age_min
age_max
city_tier
cibil_range_hint
existing_relationship_with_bank
salary_account_required
pincode_coverage
documents_required
```

### 5) India-Specific Fields

```
rupay_upi_supported
upi_reward_rate

fuel_surcharge_waiver

domestic_lounge_visits
international_lounge_visits

forex_markup_percentage

movie_benefits
dining_benefits

railway_lounge_access
golf_benefits

reward_expiry_months

annual_fee_waiver_spend

salary_account_benefit

card_network
(Visa/Mastercard/RuPay/Amex)
```