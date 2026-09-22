"""
eSavadh - Legal Notice & Compounding Settlement Generator
Made by Team Avyukt

Prepares structured draft legal notices and compounding calculations under 
Sections 18, 48, and 49 of the Legal Metrology Act, 2009.
All notices are explicitly marked: DRAFT — SUBJECT TO AUTHORIZED REVIEW.
"""

from datetime import datetime


def generate_draft_notice(inspection_ref, recipient_name, recipient_address, violations, officer_name, officer_designation):
    """
    Generates a legally structured Draft Notice based on verified inspection findings.
    """
    notice_date = datetime.now().strftime("%d %B %Y")
    notice_ref_no = f"LM/ENF/{datetime.now().strftime('%Y')}/{inspection_ref}"
    
    violation_bullets = []
    for idx, raw_v in enumerate(violations, 1):
        v = dict(raw_v) if not isinstance(raw_v, dict) else raw_v
        violation_bullets.append(
            f"{idx}. Violation of {v.get('legal_section', 'Legal Metrology Rules')}:\n"
            f"   • Observed Deficiency: {v.get('observed_value', 'Missing mandatory declaration')}\n"
            f"   • Statutory Requirement: {v.get('expected_value', 'Standard declaration')}\n"
            f"   • Finding Detail: {v.get('finding_note', 'Non-compliance observed during routine market surveillance.')}"
        )
        
    violations_text = "\n\n".join(violation_bullets) if violation_bullets else "1. General non-compliance of mandatory packaging declarations under Rule 6 of PCR 2011."
    
    draft_text = f"""GOVERNMENT OF INDIA
MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION
DEPARTMENT OF CONSUMER AFFAIRS
LEGAL METROLOGY DIVISION (ENFORCEMENT WING)

================================================================================
NOTICE UNDER SECTION 18 READ WITH SECTION 49 OF THE LEGAL METROLOGY ACT, 2009
AND RULE 32 OF THE LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011
================================================================================

NOTICE REFERENCE NO: {notice_ref_no}
INSPECTION DOSSIER REF: {inspection_ref}
DATE OF ISSUANCE: {notice_date}

TO:
{recipient_name}
{recipient_address}

SUBJECT: SHOW CAUSE NOTICE FOR CONTRAVENTION OF PROVISIONS OF THE LEGAL METROLOGY ACT, 2009 AND PACKAGED COMMODITIES RULES, 2011.

WHEREAS, an official inspection/market surveillance was conducted on the packaged commodities distributed/marketed/manufactured by you, bearing Inspection Reference Number {inspection_ref};

AND WHEREAS, upon examination of the principal display panel and packaging declarations of the subject commodity, the following statutory contraventions have been recorded:

{violations_text}

NOW THEREFORE, take notice that by selling/distributing/packing the said pre-packaged commodity in contravention of the mandatory provisions, you have rendered yourself liable for penal action under Section 36 of the Legal Metrology Act, 2009.

YOU ARE HEREBY CALLED UPON to submit your written explanation along with supporting documentary evidence within FIFTEEN (15) DAYS from the receipt of this notice, explaining why prosecution proceedings should not be initiated against you before the Competent Court of Law.

TAKE FURTHER NOTICE that if you wish to apply for compounding of the offense under Section 48 of the Legal Metrology Act, 2009, you may submit a formal compounding application within the stipulated time frame.

Given under my hand and official seal on this {notice_date}.

--------------------------------------------------------------------------------
[OFFICIAL SIGNATURE / SEAL]

{officer_name}
{officer_designation}
Enforcement Wing, Directorate of Legal Metrology

*** DRAFT NOTICE — SUBJECT TO AUTHORIZED LEGAL REVIEW BEFORE DISPATCH ***
"""
    return {
        "notice_ref_no": notice_ref_no,
        "notice_date": notice_date,
        "draft_text": draft_text
    }


def calculate_compounding_fee(violation_count, recipient_role="Manufacturer", is_repeat_offense=False):
    """
    Calculates compounding fee guidelines under Section 48 of Legal Metrology Act, 2009.
    Section 48 allows compounding of certain offenses before or after institution of prosecution.
    """
    if recipient_role in ["Manufacturer", "Packer", "Importer"]:
        base_fee = 25000.0  # Statutory baseline for manufacturers under Sec 36(1)
    else:
        base_fee = 5000.0   # Statutory baseline for retailers

    if is_repeat_offense:
        compounded_amount = base_fee * 2.0
        offense_clause = "Section 48 read with Section 36(1) [Second/Repeated Offense - Aggravated]"
    else:
        # Scale slightly per additional violation count
        compounded_amount = base_fee + (max(0, violation_count - 1) * 2500.0)
        offense_clause = "Section 48 read with Section 36(1) [First Offense - Compoundable]"
        
    return {
        "offense_clause": offense_clause,
        "base_fee": base_fee,
        "calculated_amount": compounded_amount,
        "eligibility": "Eligible for Compounding (Subject to Director/Controller Approval)",
        "statutory_note": "Under Section 48(1), sum accepted by way of composition cannot exceed the maximum fine provided under the Act."
    }
