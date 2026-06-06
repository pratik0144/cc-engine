"""
Pydantic models for Indian credit/debit card data.
Matches all fields from details.md across 5 categories.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ── 1. Card Master Data ────────────────────────────────────────────────────
class CardMaster(BaseModel):
    """Core identity fields for a card."""
    card_name: str = Field(..., description="Official name of the card")
    bank_name: str = Field(..., description="Issuing bank name")
    card_type: Optional[str] = Field(None, description="credit or debit")
    card_network: Optional[str] = Field(None, description="Visa/Mastercard/RuPay/Amex")
    variant: Optional[str] = Field(None, description="classic/platinum/signature/infinite/etc.")
    card_category: Optional[str] = Field(None, description="cashback/travel/fuel/entry-level/student/luxury/etc.")
    official_url: Optional[str] = Field(None, description="URL of the card's detail page")
    status: Optional[str] = Field("active", description="active or discontinued")
    launch_date: Optional[str] = Field(None, description="Launch date if known")


# ── 2. Pricing / Fees ─────────────────────────────────────────────────────
class PricingFees(BaseModel):
    """All fee-related fields."""
    joining_fee: Optional[str] = Field(None, description="One-time joining/issuance fee (e.g. '500', 'Nil', '999+GST')")
    annual_fee: Optional[str] = Field(None, description="Yearly recurring fee")
    annual_fee_waiver_condition: Optional[str] = Field(None, description="Condition to waive annual fee (e.g. 'Spend 2L in a year')")
    annual_fee_waiver_spend: Optional[str] = Field(None, description="Spend amount to waive annual fee")
    late_payment_fee: Optional[str] = Field(None, description="Fee for late payment")
    cash_withdrawal_fee: Optional[str] = Field(None, description="Fee for cash advance/withdrawal")
    forex_markup: Optional[str] = Field(None, description="Foreign currency transaction markup percentage")
    cashback_cap_fee: Optional[str] = Field(None, description="Monthly/yearly cashback cap")
    reward_redemption_fee: Optional[str] = Field(None, description="Fee for redeeming rewards")
    add_on_card_fee: Optional[str] = Field(None, description="Fee for supplementary/add-on cards")


# ── 3. Benefit Engine Data ─────────────────────────────────────────────────
class Benefits(BaseModel):
    """Rewards, offers, and benefits."""
    reward_type: Optional[str] = Field(None, description="points/cashback/miles")
    reward_rate_general: Optional[str] = Field(None, description="Base reward rate (e.g. '1 point per ₹100')")
    reward_rate_category_wise: Optional[dict] = Field(None, description="Category-specific reward rates as key-value pairs")
    bonus_categories: Optional[list[str]] = Field(None, description="Categories with bonus rewards")
    welcome_bonus: Optional[str] = Field(None, description="Welcome/signup bonus details")
    milestone_bonuses: Optional[list[str]] = Field(None, description="Spend milestone bonus details")
    fuel_surcharge_waiver: Optional[str] = Field(None, description="Fuel surcharge waiver details")
    lounge_access: Optional[str] = Field(None, description="Airport lounge access details")
    airport_meet_greet: Optional[str] = Field(None, description="Airport meet & greet service details")
    movie_offer: Optional[str] = Field(None, description="Movie ticket offers (e.g. BookMyShow)")
    dining_offer: Optional[str] = Field(None, description="Dining/restaurant offers")
    grocery_offer: Optional[str] = Field(None, description="Grocery shopping offers")
    travel_benefits: Optional[str] = Field(None, description="Travel-related benefits (hotel, flight discounts)")
    insurance_benefits: Optional[str] = Field(None, description="Insurance coverage details")
    emi_conversions: Optional[str] = Field(None, description="EMI conversion facility details")
    contactless_support: Optional[str] = Field(None, description="Contactless/tap-to-pay/UPI support")


# ── 4. Eligibility + Approval Likelihood ───────────────────────────────────
class Eligibility(BaseModel):
    """Eligibility criteria for card application."""
    minimum_income: Optional[str] = Field(None, description="Minimum annual/monthly income required")
    employment_type: Optional[str] = Field(None, description="Salaried/self-employed/business")
    age_min: Optional[str] = Field(None, description="Minimum age for application")
    age_max: Optional[str] = Field(None, description="Maximum age for application")
    city_tier: Optional[str] = Field(None, description="City tier restrictions if any")
    cibil_range_hint: Optional[str] = Field(None, description="Approximate CIBIL score needed (e.g. '750+')")
    existing_relationship_with_bank: Optional[str] = Field(None, description="Existing bank relationship requirement")
    salary_account_required: Optional[str] = Field(None, description="Whether salary account is needed")
    pincode_coverage: Optional[str] = Field(None, description="Serviceable pincode/city restrictions")
    documents_required: Optional[list[str]] = Field(None, description="Required documents for application")


# ── 5. India-Specific Fields ───────────────────────────────────────────────
class IndiaSpecific(BaseModel):
    """India-specific card features."""
    rupay_upi_supported: Optional[str] = Field(None, description="Whether RuPay UPI is supported")
    upi_reward_rate: Optional[str] = Field(None, description="Reward rate for UPI transactions")
    domestic_lounge_visits: Optional[str] = Field(None, description="Number of domestic lounge visits per quarter/year")
    international_lounge_visits: Optional[str] = Field(None, description="Number of international lounge visits per quarter/year")
    forex_markup_percentage: Optional[str] = Field(None, description="Forex markup as a percentage")
    movie_benefits: Optional[str] = Field(None, description="Movie-specific benefits (BookMyShow/Paytm)")
    dining_benefits: Optional[str] = Field(None, description="Dining-specific benefits (Zomato/Swiggy/EazyDiner)")
    railway_lounge_access: Optional[str] = Field(None, description="Railway lounge access details")
    golf_benefits: Optional[str] = Field(None, description="Golf course access/benefits")
    reward_expiry_months: Optional[str] = Field(None, description="Reward points expiry period in months")
    salary_account_benefit: Optional[str] = Field(None, description="Additional benefits for salary account holders")


# ── Composite Card Model ──────────────────────────────────────────────────
class CreditCard(BaseModel):
    """
    Complete credit/debit card data model.
    Combines all sub-models into a single flat-ish structure for JSON output.
    """
    # Identity
    card_id: Optional[str] = Field(None, description="Auto-generated unique ID")
    bank_id: Optional[str] = Field(None, description="Auto-generated bank ID")
    last_verified_at: Optional[str] = Field(None, description="ISO timestamp of last verification")
    source_url: Optional[str] = Field(None, description="URL the data was scraped from")

    # Sub-models
    master: CardMaster
    pricing: Optional[PricingFees] = Field(default_factory=PricingFees)
    benefits: Optional[Benefits] = Field(default_factory=Benefits)
    eligibility: Optional[Eligibility] = Field(default_factory=Eligibility)
    india_specific: Optional[IndiaSpecific] = Field(default_factory=IndiaSpecific)


# ── LLM Extraction Schema (flat version for prompting) ────────────────────
class CardExtraction(BaseModel):
    """
    Flat model used for LLM extraction prompts.
    Easier for the LLM to fill than nested models.
    """
    # Card Master
    card_name: str = Field(..., description="Official name of the credit/debit card")
    bank_name: str = Field(..., description="Name of the issuing bank")
    card_type: Optional[str] = Field(None, description="credit or debit")
    card_network: Optional[str] = Field(None, description="Visa, Mastercard, RuPay, or Amex")
    variant: Optional[str] = Field(None, description="Card tier: classic, gold, platinum, signature, infinite, etc.")
    card_category: Optional[str] = Field(None, description="Primary category: cashback, travel, fuel, rewards, lifestyle, premium, entry-level, student, luxury, business, shopping")
    status: Optional[str] = Field("active", description="active or discontinued")
    launch_date: Optional[str] = Field(None, description="Card launch date if mentioned")

    # Pricing / Fees
    joining_fee: Optional[str] = Field(None, description="One-time joining fee in INR (e.g. '500', 'Nil', '999+GST')")
    annual_fee: Optional[str] = Field(None, description="Annual recurring fee in INR")
    annual_fee_waiver_condition: Optional[str] = Field(None, description="Condition to get annual fee waived")
    annual_fee_waiver_spend: Optional[str] = Field(None, description="Spend amount in INR to waive annual fee")
    late_payment_fee: Optional[str] = Field(None, description="Late payment penalty")
    cash_withdrawal_fee: Optional[str] = Field(None, description="Cash advance fee")
    forex_markup: Optional[str] = Field(None, description="Foreign currency markup percentage")
    cashback_cap_fee: Optional[str] = Field(None, description="Maximum cashback limit per month/year")
    reward_redemption_fee: Optional[str] = Field(None, description="Fee to redeem reward points")
    add_on_card_fee: Optional[str] = Field(None, description="Add-on/supplementary card fee")

    # Benefits
    reward_type: Optional[str] = Field(None, description="points, cashback, or miles")
    reward_rate_general: Optional[str] = Field(None, description="Base earn rate (e.g. '2 points per ₹100 spent')")
    reward_rate_category_wise: Optional[dict] = Field(None, description="Category-wise earn rates as {category: rate}")
    bonus_categories: Optional[list[str]] = Field(None, description="Categories with bonus/accelerated rewards")
    welcome_bonus: Optional[str] = Field(None, description="Welcome/signup bonus")
    milestone_bonuses: Optional[list[str]] = Field(None, description="Spend milestone bonuses")
    fuel_surcharge_waiver: Optional[str] = Field(None, description="Fuel surcharge waiver details and limits")
    lounge_access: Optional[str] = Field(None, description="Domestic and international airport lounge access")
    airport_meet_greet: Optional[str] = Field(None, description="Airport meet and greet service")
    movie_offer: Optional[str] = Field(None, description="Movie ticket offers")
    dining_offer: Optional[str] = Field(None, description="Dining and restaurant offers")
    grocery_offer: Optional[str] = Field(None, description="Grocery/supermarket offers")
    travel_benefits: Optional[str] = Field(None, description="Travel benefits like hotel/flight bookings")
    insurance_benefits: Optional[str] = Field(None, description="Insurance coverage included")
    emi_conversions: Optional[str] = Field(None, description="EMI conversion facility")
    contactless_support: Optional[str] = Field(None, description="Tap-to-pay and UPI support")

    # Eligibility
    minimum_income: Optional[str] = Field(None, description="Minimum income required (annual or monthly)")
    employment_type: Optional[str] = Field(None, description="Eligible employment types")
    age_min: Optional[str] = Field(None, description="Minimum age")
    age_max: Optional[str] = Field(None, description="Maximum age")
    city_tier: Optional[str] = Field(None, description="City restrictions if any")
    cibil_range_hint: Optional[str] = Field(None, description="Indicative CIBIL score needed")
    existing_relationship_with_bank: Optional[str] = Field(None, description="Existing relationship requirement")
    salary_account_required: Optional[str] = Field(None, description="Salary account requirement")
    pincode_coverage: Optional[str] = Field(None, description="Serviceable areas")
    documents_required: Optional[list[str]] = Field(None, description="Documents needed to apply")

    # India-Specific
    rupay_upi_supported: Optional[str] = Field(None, description="RuPay UPI support")
    upi_reward_rate: Optional[str] = Field(None, description="Rewards on UPI transactions")
    domestic_lounge_visits: Optional[str] = Field(None, description="Domestic lounge visits per quarter/year")
    international_lounge_visits: Optional[str] = Field(None, description="International lounge visits per quarter/year")
    forex_markup_percentage: Optional[str] = Field(None, description="Forex markup %")
    movie_benefits: Optional[str] = Field(None, description="Movie benefits details")
    dining_benefits: Optional[str] = Field(None, description="Dining benefits details")
    railway_lounge_access: Optional[str] = Field(None, description="Railway lounge access")
    golf_benefits: Optional[str] = Field(None, description="Golf course access")
    reward_expiry_months: Optional[str] = Field(None, description="Reward point expiry in months")
    salary_account_benefit: Optional[str] = Field(None, description="Salary account benefits")
