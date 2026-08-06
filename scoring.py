from config import REVIEW_COUNT_THRESHOLD
from datetime import datetime, timedelta


def score_lead(lead_data):
    """
    Score and flag a lead based on multiple criteria.
    Returns a dict with flags and priority_score.
    """
    flags = {
        'no_website': False,
        'low_reviews': False,
        'possibly_inactive': False,
    }
    priority_score = 0.0

    # Flag: No website (highest priority)
    if not lead_data.get('website'):
        flags['no_website'] = True
        priority_score += 100

    # Flag: Low review count despite appearing established
    review_count = lead_data.get('review_count', 0)
    if review_count > 0 and review_count < REVIEW_COUNT_THRESHOLD:
        flags['low_reviews'] = True
        priority_score += 50

    # Flag: Possibly inactive (no reviews recently, low engagement)
    if review_count == 0:
        flags['possibly_inactive'] = True
        priority_score += 30

    # Boost score for businesses with no website AND low reviews
    if flags['no_website'] and flags['low_reviews']:
        priority_score += 25

    return {
        'flags': flags,
        'priority_score': priority_score,
    }


def apply_scoring_to_lead(lead_db_obj, scoring_result):
    """Apply scoring results to a database Lead object."""
    lead_db_obj.no_website = scoring_result['flags']['no_website']
    lead_db_obj.low_reviews = scoring_result['flags']['low_reviews']
    lead_db_obj.possibly_inactive = scoring_result['flags']['possibly_inactive']
    lead_db_obj.priority_score = scoring_result['priority_score']
    return lead_db_obj
