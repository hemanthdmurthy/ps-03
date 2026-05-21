"""
Smart Normalization Layer
=========================
Performs preprocessing and standardization on raw company records 
before they enter the validation engine.
"""

import re
from typing import Any, Dict, Optional, Tuple, List

def clean_string(value: Any, fallback: str = "") -> str:
    """
    Remove leading/trailing spaces and handle sentinel/placeholder string values.
    Converts 'N/A', 'null', 'none' variations to the fallback.
    """
    if value is None:
        return fallback
    val_str = str(value).strip()
    if val_str.lower() in ("null", "n/a", "none", "nan", "undefined", ""):
        return fallback
    return val_str

def normalize_url(url: Any) -> str:
    """
    Standardize website URLs:
    - Lowercase domain names.
    - Standardize schema to https://.
    - Remove trailing slash.
    - Add missing 'www.' if missing or keep subdomain if present.
    """
    url_str = clean_string(url)
    if not url_str:
        return ""
    
    # Remove leading/trailing whitespaces and tabs
    url_str = url_str.strip().lower()
    
    # Handle protocol
    if url_str.startswith("http://"):
        url_str = "https://" + url_str[7:]
    elif not url_str.startswith("https://"):
        url_str = "https://" + url_str
        
    # Remove trailing slash
    if url_str.endswith("/"):
        url_str = url_str[:-1]
        
    # Parse domain and adjust structure if needed
    # Example: https://google.com -> https://www.google.com
    match = re.match(r"https://([^/]+)(.*)", url_str)
    if match:
        domain = match.group(1)
        path = match.group(2) or ""
        
        # If domain has no subdomains and isn't localhost/ip, prepend www.
        # Simple heuristic: domain has only one dot (e.g., google.com)
        parts = domain.split(".")
        if len(parts) == 2 and not domain.startswith("www."):
            domain = "www." + domain
            
        url_str = f"https://{domain}{path}"
        
    return url_str

def normalize_email(email: Any) -> str:
    """
    Standardize emails:
    - Lowercase.
    - Remove outer whitespace.
    """
    email_str = clean_string(email)
    if not email_str:
        return ""
    return email_str.strip().lower()

def normalize_phone(phone: Any) -> str:
    """
    Standardize phone numbers into clean digits, retaining leading '+' for country codes.
    E.g., "+1 (555) 019-2834" -> "+15550192834"
    """
    phone_str = clean_string(phone)
    if not phone_str:
        return ""
    
    # Retain '+' if it's the first character
    has_plus = phone_str.startswith("+")
    # Strip all non-digits
    digits = "".join(char for char in phone_str if char.isdigit())
    
    if not digits:
        return ""
        
    return f"+{digits}" if has_plus else digits

def normalize_year(year_val: Any) -> Optional[int]:
    """
    Extract a clean 4-digit year from messy strings/integers.
    E.g., "Founded in 2013" -> 2013, "2015-06-12" -> 2015, 2014.0 -> 2014
    """
    if year_val is None:
        return None
        
    year_str = str(year_val).strip()
    # Match any 4-digit sequence starting with 19 or 20
    match = re.search(r"\b(19\d{2}|20\d{2})\b", year_str)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
            
    return None

def normalize_enum(val: Any, field_name: str) -> str:
    """
    Standardize common classifications like Nature of Company, Category, and GTM Motion.
    """
    val_str = clean_string(val)
    if not val_str:
        return ""
        
    normalized = val_str.lower().replace("_", " ").replace("-", " ").strip()
    
    if field_name == "nature_of_company":
        if "pvt" in normalized or "private" in normalized:
            return "Private"
        if "public" in normalized or "ltd" in normalized:
            return "Public"
        if "proprietorship" in normalized:
            return "Sole Proprietorship"
        if "partnership" in normalized:
            return "Partnership"
            
    elif field_name == "category":
        if "saas" in normalized or "software as a service" in normalized:
            return "SaaS"
        if "b2b" in normalized and "enterprise" in normalized:
            return "B2B Enterprise"
        if "fintech" in normalized or "financial technology" in normalized:
            return "Fintech"
        if "consulting" in normalized or "services" in normalized:
            return "IT Services & Consulting"
            
    elif field_name == "gtm_motion":
        if "product led" in normalized or "plg" in normalized:
            return "PLG"
        if "enterprise" in normalized or "sales led" in normalized or "slg" in normalized:
            return "Enterprise SLG"
        if "hybrid" in normalized:
            return "Hybrid"
        if "b2b" in normalized or "b2b2c" in normalized:
            return "B2B"
            
    # Fallback to standard Title Case if no special enum mapping is defined
    return val_str.title()

def normalize_company_name(name: Any) -> str:
    """
    Standardize company name casing:
    - Retain uppercase for known acronyms (IBM, TCS, BMW, SAP, AWS, TCS, QNX, Acko, etc.)
    - Clean up trailing corporate suffixes to match rules if necessary (e.g. resolving spacing before Ltd)
    - Fallback to clean Title Case.
    """
    name_str = clean_string(name)
    if not name_str:
        return ""
        
    # Standardize known acronyms
    acronyms = {"ibm": "IBM", "tcs": "TCS", "bmw": "BMW", "sap": "SAP", "aws": "AWS", "qnx": "QNX", "it": "IT", "llc": "LLC", "plc": "PLC"}
    
    words = name_str.split()
    cleaned_words = []
    for word in words:
        word_clean = word.lower().replace(",", "").replace(".", "").strip()
        if word_clean in acronyms:
            cleaned_words.append(acronyms[word_clean])
        else:
            # Capitalize word while keeping some original caps if it's already camelCased (e.g., "DreamPlug", "BharatPe")
            if any(c.isupper() for c in word[1:]) and word[0].isupper():
                cleaned_words.append(word)
            else:
                cleaned_words.append(word.capitalize())
                
    return " ".join(cleaned_words)

def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocess all keys of a single company record before validation.
    """
    normalized = record.copy()
    
    # 1. Identity
    normalized["company_name"] = normalize_company_name(record.get("company_name", ""))
    normalized["short_name"] = normalize_company_name(record.get("short_name", ""))
    
    # 2. URLs & Contact Details
    normalized["website_url"] = normalize_url(record.get("website_url", ""))
    normalized["logo_url"] = normalize_url(record.get("logo_url", ""))
    normalized["contact_person_email"] = normalize_email(record.get("contact_person_email", ""))
    normalized["contact_person_phone"] = normalize_phone(record.get("contact_person_phone", ""))
    
    # 3. Enums & Metadata
    normalized["nature_of_company"] = normalize_enum(record.get("nature_of_company", ""), "nature_of_company")
    normalized["category"] = normalize_enum(record.get("category", ""), "category")
    normalized["gtm_motion"] = normalize_enum(record.get("gtm_motion", ""), "gtm_motion")
    
    # 4. Temporal (Year of Incorporation)
    year = record.get("year_of_incorporation")
    norm_year = normalize_year(year)
    if norm_year is not None:
        normalized["year_of_incorporation"] = norm_year
        
    return normalized
