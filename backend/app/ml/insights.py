"""
MediTrack AI Insight & Clinical Intervention Generator
Translates risk scores and patient feature dynamics into actionable recommendations
for clinic receptionists and care coordinators.
"""
from typing import Dict, Any, List

def generate_clinical_interventions(appointment: Dict[str, Any], risk_score: float) -> Dict[str, Any]:
    """
    Generates actionable, specific clinical outreach steps based on patient risk drivers.
    """
    risk_factors: List[str] = []
    recommended_actions: List[str] = []
    
    lead_days = appointment.get("lead_days", 0)
    prior_no_shows = appointment.get("prior_no_shows", 0)
    prior_appointments = appointment.get("prior_appointments", 0)
    sms_reminder = appointment.get("sms_reminder", False)
    age = appointment.get("age", 40)
    hour = appointment.get("hour", 10)
    day_of_week = appointment.get("day_of_week", 1)
    dept = appointment.get("department", "General Medicine")
    
    # Analyze Risk Factors
    if lead_days >= 14:
        risk_factors.append(f"Extended lead time ({lead_days} days since booking)")
        recommended_actions.append("Dispatch WhatsApp 24h & 2h pre-appointment confirmation prompt")
    elif lead_days >= 7:
        risk_factors.append(f"Moderate lead time ({lead_days} days)")
        
    if prior_no_shows > 0:
        ratio = (prior_no_shows / max(prior_appointments, 1)) * 100
        risk_factors.append(f"Past no-show record ({prior_no_shows} misses, {ratio:.0f}% historical no-show rate)")
        recommended_actions.append("Direct phone call from clinic coordinator to confirm attendance")
    elif prior_appointments == 0:
        risk_factors.append("First-time clinic patient (no adherence baseline)")
        recommended_actions.append("Send clinic location map, parking guidance, and pre-registration link")
        
    if not sms_reminder:
        risk_factors.append("Automated SMS reminder NOT enabled")
        recommended_actions.append("Enable automated SMS reminder schedule immediately")
        
    if hour in [8, 17]:
        time_str = "Early morning (8:00 AM)" if hour == 8 else "End-of-day (5:00 PM)"
        risk_factors.append(f"Peak traffic appointment window: {time_str}")
        recommended_actions.append("Verify transportation readiness and clinic arrival buffer")
        
    if day_of_week in [0, 4]:
        day_str = "Monday" if day_of_week == 0 else "Friday"
        risk_factors.append(f"Higher variance scheduling day ({day_str})")
        
    if age >= 75:
        recommended_actions.append("Offer caregiver notification or patient transport assistance")
    elif age < 25:
        recommended_actions.append("Send digital mobile check-in link for quick turnaround")
        
    # Department specific guidance
    if dept in ["Cardiology", "Neurology"] and risk_score >= 0.40:
        recommended_actions.append(f"Critical specialty ({dept}): Flag doctor schedule for standby waitlist patient if unconfirmed 3h prior")
        
    # Fallback if low risk
    if not risk_factors:
        risk_factors.append("Standard appointment profile with high historical adherence")
    if not recommended_actions:
        recommended_actions.append("Standard automated SMS confirmation 24h prior")
        
    # Determine primary headline action
    if risk_score >= 0.50:
        headline = "URGENT OUTREACH: High risk of no-show. Require direct telephone confirmation & prepare waitlist standby."
    elif risk_score >= 0.25:
        headline = "PROACTIVE NOTICE: Send WhatsApp interactive RSVP and remind patient of appointment."
    else:
        headline = "STANDARD MONITORING: Low risk. Maintain standard automated reminder workflow."
        
    return {
        "headline": headline,
        "risk_factors": risk_factors[:4],
        "recommended_actions": recommended_actions[:3],
        "revenue_impact_estimate": 120.0 # Average outpatient visit revenue in USD
    }
