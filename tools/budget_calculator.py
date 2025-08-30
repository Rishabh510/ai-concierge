"""
Budget Calculator Tool for Wedding Services
Calculates estimated costs for décor, photography, and catering based on event details.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("budget-calculator")


def calculate_budget(number_of_events: int, number_of_people: int, location: str) -> Dict[str, Any]:
    """
    Calculate wedding service budget based on events, people count, and location.

    Args:
        number_of_events: Number of wedding events (wedding, reception, etc.)
        number_of_people: Total number of guests across all events
        location: City/location for the wedding

    Returns:
        Dictionary with budget breakdown and total
    """

    # Base rates per person (in INR)
    base_rates = {
        "decor": 3000,  # ₹3000 per person for décor
        "photography": 1800,  # ₹1800 per person for photography
        "catering": 500,  # ₹500 per person for catering
    }

    # Location multipliers (cost varies by city)
    location_multipliers = {
        "mumbai": 1.3,
        "delhi": 1.2,
        "bangalore": 1.1,
        "hyderabad": 1.0,
        "goa": 1.1,
        "rajasthan": 1.0,
        "chennai": 1.0,
        "kolkata": 1.0,
        "pune": 1.0,
        "ahmedabad": 0.9,
    }

    # Get location multiplier (default to 1.0 if location not found)
    location_lower = location.lower().strip()
    multiplier = location_multipliers.get(location_lower, 1.0)

    # Calculate base costs
    decor_cost = base_rates["decor"] * number_of_people * multiplier
    photography_cost = base_rates["photography"] * number_of_people * multiplier
    catering_cost = base_rates["catering"] * number_of_people * multiplier

    # Apply event multiplier (more events = higher total cost)
    event_multiplier = min(1.5, 1.0 + (number_of_events - 1) * 0.25)

    # Calculate final costs
    final_decor = decor_cost * event_multiplier
    final_photography = photography_cost * event_multiplier
    final_catering = catering_cost * event_multiplier

    total_budget = final_decor + final_photography + final_catering

    # Convert to lakhs (1 lakh = 100,000 INR)
    result = {
        "decor_budget_lakhs": round(final_decor / 100000, 2),
        "photography_budget_lakhs": round(final_photography / 100000, 2),
        "catering_budget_lakhs": round(final_catering / 100000, 2),
        "total_budget_lakhs": round(total_budget / 100000, 2),
        "location": location,
        "number_of_events": number_of_events,
        "number_of_people": number_of_people,
        "location_multiplier": multiplier,
        "event_multiplier": event_multiplier,
    }

    logger.info(f"Budget calculated: {result}")
    return result


def format_budget_for_speech(budget_data: Dict[str, Any]) -> str:
    """
    Format budget data for speech output.

    Args:
        budget_data: Budget calculation result

    Returns:
        Formatted string for speech
    """
    decor = budget_data["decor_budget_lakhs"]
    photo = budget_data["photography_budget_lakhs"]
    catering = budget_data["catering_budget_lakhs"]
    total = budget_data["total_budget_lakhs"]

    # Format numbers for speech (e.g., 1.00 -> "1 lakh", 1.50 -> "one point five lakhs")
    def format_lakhs(value):
        if value == int(value):
            return f"{int(value)} lakh"
        else:
            # Convert to words for speech
            words = {
                0.25: "point two five",
                0.30: "point three",
                0.40: "point four",
                0.50: "point five",
                0.60: "point six",
                0.70: "point seven",
                0.80: "point eight",
                0.90: "point nine",
                1.00: "one",
                1.25: "one point two five",
                1.30: "one point three",
                1.40: "one point four",
                1.50: "one point five",
                1.60: "one point six",
                1.70: "one point seven",
                1.80: "one point eight",
                1.90: "one point nine",
                2.00: "two",
                3.00: "three",
                4.00: "four",
                5.00: "five",
                6.00: "six",
                7.00: "seven",
                8.00: "eight",
                9.00: "nine",
                10.00: "ten",
            }
            return f"{words.get(value, str(value))} lakhs"

    return f"Décor: ₹{format_lakhs(decor)} lakhs, Photography: ₹{format_lakhs(photo)} lakhs, Catering: ₹{format_lakhs(catering)} lakhs. Total estimated budget: ₹{format_lakhs(total)} lakhs."
