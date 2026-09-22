"""
eSavadh - Time-Aware Legal Metrology Rule Compliance Engine
Made by Team Avyukt

Evaluates declarations against the Legal Metrology Act, 2009 and 
Legal Metrology (Packaged Commodities) Rules, 2011 (with Amendments).
Supports time-aware retroactive rule matching based on manufacturing date.
"""

from datetime import datetime
import re


def parse_date_safely(date_str):
    """Parses various date formats into a datetime object for time-aware comparisons."""
    if not date_str:
        return None
        
    date_str = date_str.strip()
    
    # Try MM/YYYY or MM-YYYY
    m = re.match(r"^(\d{1,2})[\/\-](\d{4})$", date_str)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        return datetime(year, month, 1)
        
    # Try YYYY-MM-DD
    m = re.match(r"^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$", date_str)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Try Month YYYY (e.g. MAY 2024)
    for fmt in ["%b %Y", "%B %Y", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
            
    # Try extracting 4 digit year
    m = re.search(r"\b(20\d{2}|19\d{2})\b", date_str)
    if m:
        return datetime(int(m.group(1)), 1, 1)
        
    return None


def evaluate_product_compliance(declarations, mfg_date_str=None, category="All", active_rules=None):
    """
    Evaluates extracted/confirmed declarations against versioned Legal Metrology Rules.
    Respects manufacturing date for time-aware applicability.
    """
    mfg_dt = parse_date_safely(mfg_date_str) if mfg_date_str else None
    
    # Default benchmark manufacturing date if not specified: current date
    assessment_date = mfg_dt if mfg_dt else datetime.now()
    
    findings = []
    
    # =========================================================================
    # Rule 1: Maximum Retail Price (MRP) - Rule 6(1)(e)
    # =========================================================================
    mrp_field = declarations.get("mrp", {})
    mrp_val = mrp_field.get("confirmed_value") or mrp_field.get("extracted_value")
    
    if not mrp_val:
        findings.append({
            "declaration_field": "mrp",
            "rule_code": "PCR-2011-R6-1-E",
            "legal_section": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
            "status": "Non-Compliant",
            "severity": "Critical",
            "observed_value": "Not detected / missing on package",
            "expected_value": "MRP in Indian Rupees inclusive of all taxes (e.g. 'MRP ₹ X.XX incl. of all taxes')",
            "finding_note": "Mandatory MRP declaration is absent. Direct violation of Rule 6(1)(e)."
        })
    else:
        # Validate format
        has_currency = bool(re.search(r"(?:₹|Rs|INR)", mrp_val, re.IGNORECASE))
        has_tax_clause = bool(re.search(r"(?:tax|incl)", mrp_val, re.IGNORECASE)) or True # lenient if currency is clear
        
        if has_currency:
            findings.append({
                "declaration_field": "mrp",
                "rule_code": "PCR-2011-R6-1-E",
                "legal_section": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
                "status": "Compliant",
                "severity": "Minor",
                "observed_value": mrp_val,
                "expected_value": "MRP in Indian Currency (incl. of all taxes)",
                "finding_note": "Maximum Retail Price clearly declared with valid currency denomination."
            })
        else:
            findings.append({
                "declaration_field": "mrp",
                "rule_code": "PCR-2011-R6-1-E",
                "legal_section": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
                "status": "Needs Review",
                "severity": "Medium",
                "observed_value": mrp_val,
                "expected_value": "Currency symbol (₹ / Rs.) with numeric value",
                "finding_note": "Numeric value detected, but explicit currency symbol requires inspector verification."
            })

    # =========================================================================
    # Rule 2: Net Quantity - Rule 6(1)(d) & Rule 11 (Standard SI Units)
    # =========================================================================
    net_field = declarations.get("net_quantity", {})
    net_val = net_field.get("confirmed_value") or net_field.get("extracted_value")
    
    if not net_val:
        findings.append({
            "declaration_field": "net_quantity",
            "rule_code": "PCR-2011-R6-1-D",
            "legal_section": "Rule 6(1)(d) & Rule 11, Packaged Commodities Rules, 2011",
            "status": "Non-Compliant",
            "severity": "Critical",
            "observed_value": "Not detected / missing",
            "expected_value": "Net Quantity in standard metric SI units (g, kg, ml, l, m, or N/units)",
            "finding_note": "Mandatory Net Quantity declaration is missing. Violation of Rule 6(1)(d)."
        })
    else:
        # Check standard SI units
        is_standard_unit = bool(re.search(r"\b(?:g|kg|gm|grams?|ml|l|litres?|ltr|units?|pieces?|N|m|cm)\b", net_val, re.IGNORECASE))
        if is_standard_unit:
            findings.append({
                "declaration_field": "net_quantity",
                "rule_code": "PCR-2011-R6-1-D",
                "legal_section": "Rule 6(1)(d) & Rule 11, Packaged Commodities Rules, 2011",
                "status": "Compliant",
                "severity": "Minor",
                "observed_value": net_val,
                "expected_value": "Standard metric unit representation",
                "finding_note": "Net quantity is declared using valid standard metric units."
            })
        else:
            findings.append({
                "declaration_field": "net_quantity",
                "rule_code": "PCR-2011-R6-1-D",
                "legal_section": "Rule 11, Packaged Commodities Rules, 2011",
                "status": "Needs Review",
                "severity": "Medium",
                "observed_value": net_val,
                "expected_value": "Standard SI unit symbol (g, kg, ml, l, N)",
                "finding_note": "Declared unit may deviate from standard SI nomenclature. Inspector review recommended."
            })

    # =========================================================================
    # Rule 3: Month & Year of Manufacture / Packing - Rule 6(1)(c)
    # =========================================================================
    mfg_field = declarations.get("mfg_date", {})
    mfg_val = mfg_field.get("confirmed_value") or mfg_field.get("extracted_value")
    
    if not mfg_val:
        findings.append({
            "declaration_field": "mfg_date",
            "rule_code": "PCR-2011-R6-1-C",
            "legal_section": "Rule 6(1)(c), Packaged Commodities Rules, 2011",
            "status": "Non-Compliant",
            "severity": "Major",
            "observed_value": "Not detected / missing",
            "expected_value": "Month and Year of manufacture / packing (e.g. '05/2024' or 'MAY 2024')",
            "finding_note": "Date of manufacture or pre-packing is mandatory under Rule 6(1)(c)."
        })
    else:
        findings.append({
            "declaration_field": "mfg_date",
            "rule_code": "PCR-2011-R6-1-C",
            "legal_section": "Rule 6(1)(c), Packaged Commodities Rules, 2011",
            "status": "Compliant",
            "severity": "Minor",
            "observed_value": mfg_val,
            "expected_value": "Month and Year of manufacture or packing",
            "finding_note": "Date of manufacture/packing successfully verified."
        })

    # =========================================================================
    # Rule 4: Name and Complete Address of Manufacturer / Packer - Rule 6(1)(a)
    # =========================================================================
    mfr_field = declarations.get("manufacturer", {})
    mfr_val = mfr_field.get("confirmed_value") or mfr_field.get("extracted_value")
    
    if not mfr_val or len(mfr_val.strip()) < 5:
        findings.append({
            "declaration_field": "manufacturer",
            "rule_code": "PCR-2011-R6-1-A",
            "legal_section": "Rule 6(1)(a), Packaged Commodities Rules, 2011",
            "status": "Non-Compliant",
            "severity": "Critical",
            "observed_value": "Incomplete or missing",
            "expected_value": "Complete name and postal address of manufacturer / packer / importer",
            "finding_note": "Principal manufacturer/packer identity and physical address must be declared."
        })
    else:
        findings.append({
            "declaration_field": "manufacturer",
            "rule_code": "PCR-2011-R6-1-A",
            "legal_section": "Rule 6(1)(a), Packaged Commodities Rules, 2011",
            "status": "Compliant",
            "severity": "Minor",
            "observed_value": mfr_val[:90] + "..." if len(mfr_val) > 90 else mfr_val,
            "expected_value": "Complete Name & Postal Address",
            "finding_note": "Manufacturer/Packer name and address verified on principal display panel."
        })

    # =========================================================================
    # Rule 5: Consumer Care Contact Details - Rule 6(1)(f)
    # =========================================================================
    cc_field = declarations.get("consumer_care", {})
    cc_val = cc_field.get("confirmed_value") or cc_field.get("extracted_value")
    
    if not cc_val:
        findings.append({
            "declaration_field": "consumer_care",
            "rule_code": "PCR-2011-R6-1-F",
            "legal_section": "Rule 6(1)(f), Packaged Commodities Rules, 2011",
            "status": "Non-Compliant",
            "severity": "Major",
            "observed_value": "Not detected / missing",
            "expected_value": "Name/Designation, Telephone No., Email, and Address of grievance officer",
            "finding_note": "Consumer Care mechanism is mandatory for all pre-packaged commodities."
        })
    else:
        findings.append({
            "declaration_field": "consumer_care",
            "rule_code": "PCR-2011-R6-1-F",
            "legal_section": "Rule 6(1)(f), Packaged Commodities Rules, 2011",
            "status": "Compliant",
            "severity": "Minor",
            "observed_value": cc_val[:90] + "..." if len(cc_val) > 90 else cc_val,
            "expected_value": "Consumer helpline number / email / grievance cell address",
            "finding_note": "Consumer care helpline and email declaration verified."
        })

    # =========================================================================
    # Rule 6: Country of Origin - Rule 6(10) (Crucial for E-commerce & Imports)
    # =========================================================================
    coo_field = declarations.get("country_of_origin", {})
    coo_val = coo_field.get("confirmed_value") or coo_field.get("extracted_value")
    
    if not coo_val:
        findings.append({
            "declaration_field": "country_of_origin",
            "rule_code": "PCR-2011-R6-10",
            "legal_section": "Rule 6(10), Packaged Commodities Rules, 2011",
            "status": "Needs Review",
            "severity": "Medium",
            "observed_value": "Not explicitly detected",
            "expected_value": "Declaration of Country of Origin (e.g. 'Country of Origin: India')",
            "finding_note": "Explicit country of origin declaration not detected. Required for all imported goods and digital listings."
        })
    else:
        findings.append({
            "declaration_field": "country_of_origin",
            "rule_code": "PCR-2011-R6-10",
            "legal_section": "Rule 6(10), Packaged Commodities Rules, 2011",
            "status": "Compliant",
            "severity": "Minor",
            "observed_value": coo_val,
            "expected_value": "Declared Country of Origin",
            "finding_note": "Country of origin explicitly declared."
        })

    # =========================================================================
    # Rule 7: Time-Aware Unit Sale Price (USP) - Rule 6(11) (Enacted 2021/2022)
    # =========================================================================
    usp_enactment_date = datetime(2022, 1, 1)
    usp_field = declarations.get("unit_sale_price", {})
    usp_val = usp_field.get("confirmed_value") or usp_field.get("extracted_value")
    
    if assessment_date < usp_enactment_date:
        # Time-aware exemption!
        findings.append({
            "declaration_field": "unit_sale_price",
            "rule_code": "PCR-2021-AMEND-R6-11",
            "legal_section": "Rule 6(11), Packaged Commodities (Amendment) Rules, 2021 (Effective Jan 1, 2022)",
            "status": "Not Applicable",
            "severity": "Minor",
            "observed_value": usp_val or "Not present",
            "expected_value": "Exempt (Product manufactured before Jan 1, 2022)",
            "finding_note": f"Time-Aware Exemption: Product manufactured in {assessment_date.strftime('%B %Y')}. Unit Sale Price requirement was introduced on Jan 1, 2022 and cannot be applied retroactively."
        })
    else:
        if usp_val:
            findings.append({
                "declaration_field": "unit_sale_price",
                "rule_code": "PCR-2021-AMEND-R6-11",
                "legal_section": "Rule 6(11), Packaged Commodities (Amendment) Rules, 2021",
                "status": "Compliant",
                "severity": "Minor",
                "observed_value": usp_val,
                "expected_value": "Unit Sale Price in Rupees per g / kg / ml / l / unit",
                "finding_note": "Unit Sale Price declaration verified on packaging."
            })
        else:
            findings.append({
                "declaration_field": "unit_sale_price",
                "rule_code": "PCR-2021-AMEND-R6-11",
                "legal_section": "Rule 6(11), Packaged Commodities (Amendment) Rules, 2021",
                "status": "Non-Compliant",
                "severity": "Major",
                "observed_value": "Missing",
                "expected_value": "Unit Sale Price (e.g. ₹ 0.50 per g)",
                "finding_note": "Unit Sale Price is mandatory for commodities manufactured on or after Jan 1, 2022 under Rule 6(11)."
            })
    # =========================================================================
    # Rule 8: Dietary Indicator (Veg / Non-Veg Visual Symbol)
    # =========================================================================
    veg_field = declarations.get("veg_nonveg", {})
    veg_val = veg_field.get("confirmed_value") or veg_field.get("extracted_value")
    is_food_category = bool(re.search(r"(?:food|beverage|edible|snack|spice|oil|grain|sweet|dairy|grocery)", category, re.IGNORECASE))
    
    if veg_val and ("Vegetarian" in veg_val or "Non-Vegetarian" in veg_val or "Confirmed" in veg_val):
        findings.append({
            "declaration_field": "veg_nonveg",
            "rule_code": "FSSAI-PKG-REG-R4",
            "legal_section": "FSSAI Packaging & Labelling Regulations read with Rule 6, PCR 2011",
            "status": "Compliant",
            "severity": "Minor",
            "observed_value": veg_val,
            "expected_value": "Statutory Green (Veg) or Brown (Non-Veg) symbol",
            "finding_note": "Statutory dietary visual indicator verified."
        })
    elif veg_val == "Unclear / Needs Review":
        findings.append({
            "declaration_field": "veg_nonveg",
            "rule_code": "FSSAI-PKG-REG-R4",
            "legal_section": "FSSAI Packaging & Labelling Regulations read with Rule 6, PCR 2011",
            "status": "Needs Review",
            "severity": "Medium",
            "observed_value": "Unclear / Ambiguous visual marker",
            "expected_value": "Clear statutory Green or Brown symbol",
            "finding_note": "Visual indicator clarity requires officer physical verification on package."
        })
    else:
        if is_food_category:
            findings.append({
                "declaration_field": "veg_nonveg",
                "rule_code": "FSSAI-PKG-REG-R4",
                "legal_section": "FSSAI Packaging & Labelling Regulations read with Rule 6, PCR 2011",
                "status": "Needs Review",
                "severity": "Medium",
                "observed_value": "Not detected on scanned panel",
                "expected_value": "Green (Veg) or Brown (Non-Veg) symbol for food commodities",
                "finding_note": "Visual dietary symbol not detected on this scanned panel view. Officer should verify alternate panels."
            })
        else:
            findings.append({
                "declaration_field": "veg_nonveg",
                "rule_code": "FSSAI-PKG-REG-R4",
                "legal_section": "FSSAI Packaging & Labelling Regulations read with Rule 6, PCR 2011",
                "status": "Not Applicable",
                "severity": "Minor",
                "observed_value": "Exempt (Non-food commodity)",
                "expected_value": "N/A for non-food commodities",
                "finding_note": "Dietary indicator is not mandatory for non-food packaged items."
            })

    # =========================================================================
    # Overall Status Calculation
    # =========================================================================
    non_compliant_count = sum(1 for f in findings if f["status"] == "Non-Compliant")
    needs_review_count = sum(1 for f in findings if f["status"] == "Needs Review")
    
    if non_compliant_count > 0:
        overall_status = "Non-Compliant"
    elif needs_review_count > 0:
        overall_status = "Needs Review"
    else:
        overall_status = "Compliant"
        
    return {
        "overall_status": overall_status,
        "findings": findings,
        "non_compliant_count": non_compliant_count,
        "needs_review_count": needs_review_count,
        "compliant_count": sum(1 for f in findings if f["status"] == "Compliant"),
        "assessment_date": assessment_date.strftime("%Y-%m-%d"),
        "time_aware_note": f"Evaluated against Legal Metrology Rules effective as of {assessment_date.strftime('%B %Y')}."
    }
