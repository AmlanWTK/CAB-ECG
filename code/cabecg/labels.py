"""The shared six-label panel and how each source's labels map onto it.

Panel (rhythm and conduction findings present in PTB-XL and in at least four target cohorts):
    AF     atrial fibrillation
    IAVB   1st-degree AV block
    RBBB   (complete) right bundle branch block
    LBBB   (complete) left bundle branch block
    SB     sinus bradycardia
    STach  sinus tachycardia

AUDIT_LABELS are not predicted; they are tracked to expose labelling-convention differences
(e.g. AF coded as atrial flutter at one site, incomplete RBBB lumped with RBBB at another).
"""

PANEL = ["AF", "IAVB", "RBBB", "LBBB", "SB", "STach"]
AUDIT_LABELS = ["AFL", "IRBBB", "NSR"]

# SNOMED-CT codes used in PhysioNet/CinC Challenge 2021 headers and in ecg-arrhythmia headers.
# RBBB/CRBBB and LBBB/CLBBB are scored as equivalent by the Challenge 2021 (weights.csv).
SNOMED = {
    "AF": {"164889003"},
    "IAVB": {"270492004"},
    "RBBB": {"59118001", "713427006"},
    "LBBB": {"164909002", "733534002"},
    "SB": {"426177001"},
    "STach": {"427084000"},
    "AFL": {"164890007"},
    "IRBBB": {"713426002"},
    "NSR": {"426783006"},
}

# Abbreviation each code should carry in the Challenge 2021 dx_mapping tables (checked in the audit).
EXPECTED_ABBREVIATION = {
    "164889003": "AF",
    "270492004": "IAVB",
    "59118001": "RBBB",
    "713427006": "CRBBB",
    "164909002": "LBBB",
    "733534002": "CLBBB",
    "426177001": "SB",
    "427084000": "STach",
    "164890007": "AFL",
    "713426002": "IRBBB",
    "426783006": "NSR",
}

# PTB-XL SCP-ECG statements (scp_statements.csv). Presence in scp_codes = positive.
PTBXL_SCP = {
    "AF": {"AFIB"},
    "IAVB": {"1AVB"},
    "RBBB": {"CRBBB"},
    "LBBB": {"CLBBB"},
    "SB": {"SBRAD"},
    "STach": {"STACH"},
    "AFL": {"AFLT"},
    "IRBBB": {"IRBBB"},
    "NSR": {"SR"},
}

# CODE-15% exams.csv columns (ST = sinus tachycardia, not ST change).
CODE15_COLUMNS = {
    "AF": "AF",
    "IAVB": "1dAVb",
    "RBBB": "RBBB",
    "LBBB": "LBBB",
    "SB": "SB",
    "STach": "ST",
}


def labels_from_snomed(codes):
    """Map a collection of SNOMED codes (strings) to 0/1 panel + audit labels."""
    codes = {str(c).strip() for c in codes if str(c).strip()}
    return {name: int(bool(codes & SNOMED[name])) for name in PANEL + AUDIT_LABELS}


def labels_from_scp(scp_codes):
    """Map a PTB-XL scp_codes dict to 0/1 panel + audit labels."""
    keys = set(scp_codes)
    return {name: int(bool(keys & PTBXL_SCP[name])) for name in PANEL + AUDIT_LABELS}
