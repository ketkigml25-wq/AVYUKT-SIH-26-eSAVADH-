"""
eSavadh - E-Commerce Listing Compliance & Deduplication Engine (Section 46)
Made by Team Avyukt

Implements:
- Tier 1 (MVP/Demo): Interactive single-listing compliance checker via URL or screenshot.
- Deduplication state tracking (New, Unchanged, Changed) via content hash.
- Shared compliance pipeline reuse (OCR -> Declarations -> Rule Engine).
- Tier 2 (Future Roadmap): Outlines scheduled crawler and marketplace API integration specs.
"""

import hashlib
import re
from datetime import datetime
from core.ocr_engine import parse_declarations_from_text
from core.rule_engine import evaluate_product_compliance


def compute_listing_content_hash(platform, seller, title, text_content):
    """
    Computes a deterministic content hash for listing deduplication.
    Identifies if a listing is New, Unchanged, or Changed.
    """
    normalized = f"{platform.lower().strip()}|{seller.lower().strip()}|{title.lower().strip()}|{text_content.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def parse_ecommerce_listing_details(url_or_text, raw_text=None, platform_hint="Amazon India"):
    """
    Extracts product title, seller, declared MRP, Net Quantity, Country of Origin,
    and Manufacturer from e-commerce product pages / listing text.
    """
    content = raw_text if raw_text else url_or_text
    
    # 1. Detect Platform from URL if provided
    platform = platform_hint
    if "amazon.in" in url_or_text.lower() or "amzn" in url_or_text.lower():
        platform = "Amazon India"
    elif "flipkart.com" in url_or_text.lower():
        platform = "Flipkart"
    elif "blinkit.com" in url_or_text.lower():
        platform = "Blinkit"
    elif "zepto" in url_or_text.lower():
        platform = "Zepto"
    elif "jiomart.com" in url_or_text.lower():
        platform = "JioMart"

    # 2. Extract seller
    seller_match = re.search(r"(?:Sold\s*by|Seller|Merchant)\s*[:\-]?\s*([A-Za-z0-9\s\.,&]+?)(?:[\n\r,]|\s*and\s*fulfilled)", content, re.IGNORECASE)
    seller_name = seller_match.group(1).strip() if seller_match else "RetailNet E-Commerce Services LLP"

    # 3. Extract title
    title_match = re.search(r"(?:Title|Product\s*Name|Product)\s*[:\-]?\s*([^\n\r]{5,100})", content, re.IGNORECASE)
    if title_match:
        product_title = title_match.group(1).strip()
    else:
        first_line = content.strip().split("\n")[0]
        product_title = first_line[:80] if len(first_line) > 5 else "Packaged Commodity Online Listing"

    # 4. Use shared Legal Metrology declaration parser
    declarations = parse_declarations_from_text(content, side_hint="Listing Screenshot")
    
    # 5. Run shared time-aware rule compliance engine
    mfg_date_str = declarations.get("mfg_date", {}).get("extracted_value")
    compliance_result = evaluate_product_compliance(declarations, mfg_date_str=mfg_date_str, category="All")

    # 6. Compute content hash
    content_hash = compute_listing_content_hash(platform, seller_name, product_title, content)

    return {
        "platform": platform,
        "seller_name": seller_name,
        "product_title": product_title,
        "product_category": "Packaged Commodities / Grocery",
        "declarations": declarations,
        "compliance_result": compliance_result,
        "content_hash": content_hash,
        "overall_status": compliance_result["overall_status"],
        "tier_info": {
            "tier_level": "Tier 1 (Interactive Verification)",
            "tier_description": "Single-listing URL and screenshot ingestion pipeline actively processing."
        }
    }


def get_tier2_roadmap_spec():
    """
    Returns the formal architectural specification for Tier 2 Scheduled Marketplace Crawling.
    Explicitly documented as Future Scope / Roadmap to maintain credibility.
    """
    return {
        "status": "FUTURE ROADMAP / PRODUCTION SCOPE",
        "architecture": "Distributed scheduled crawler & Marketplace API worker pool",
        "key_components": [
            {
                "module": "Marketplace API Ingestion",
                "description": "Direct integration with official Seller APIs (Amazon SP-API, Flipkart Marketplace API) respecting rate-limits."
            },
            {
                "module": "Content-Hash Deduplicator",
                "description": "Maintains listing hash index. Skips unchanged listings to eliminate redundant OCR compute."
            },
            {
                "module": "Rate-Limited Fallback Fetcher",
                "description": "Ethical crawling respecting robots.txt when API credentials are not provisioned."
            },
            {
                "module": "Automated Officer Escalation Queue",
                "description": "Pushes flagged non-compliant listings into inspector review queues for human-in-the-loop notice drafting."
            }
        ]
    }
