"""Deterministic fictional dataset for the eServices demo portal.

All identifiers follow spec §6.6 conventions and are obviously fictional.
No randomness: content is generated from fixed sequences so ground truth and
screenshots stay reproducible.
"""

API_KEY = "lab-demo-key"

DEPARTMENTS = [
    {"id": "DEPT-REG", "name": "Registry", "description": "Civil registration and citizen records services."},
    {"id": "DEPT-PEN", "name": "Pensions", "description": "Retirement and social pension programmes."},
    {"id": "DEPT-LIC", "name": "Licensing", "description": "Business and professional licensing services."},
    {"id": "DEPT-REV", "name": "Revenue", "description": "Tax guidance, payments and certificates."},
    {"id": "DEPT-EMP", "name": "Employment", "description": "Work permits, placement and labour services."},
    {"id": "DEPT-LND", "name": "Land & Housing", "description": "Land records, tenure and housing assistance."},
]

# 9 services across 6 departments. SVC-01..03 keep the original id/name/dept
# values required by the frozen contract.
SERVICES = [
    {
        "id": "SVC-01",
        "name": "Citizen Records Lookup",
        "dept": "Registry (simulated)",
        "department_id": "DEPT-REG",
        "category": "Records",
        "summary": "Request a copy or status check of a civil registration record.",
        "description": "Use this service to look up the status of a citizen record held by the Registry. You can confirm whether a record is on file and view its current status using your record reference.",
        "needs": ["Record reference number (TEST-####)", "Registered contact phone number", "Reason for the request"],
        "steps": ["Enter your record reference.", "Provide your contact details.", "Review and submit the request.", "Note the application reference shown on screen."],
        "time": "About 10 minutes",
        "fee": "No fee",
    },
    {
        "id": "SVC-02",
        "name": "Pension Benefit Status",
        "dept": "Pensions (simulated)",
        "department_id": "DEPT-PEN",
        "category": "Benefits",
        "summary": "Check the current status of a pension benefit record.",
        "description": "Review the standing of a pension benefit for a registered participant. This demonstration service shows sample status information for fictional records only.",
        "needs": ["Record reference number (TEST-####)", "National identifier (CMTEST########)", "Preferred contact phone number"],
        "steps": ["Locate your pension record reference.", "Confirm your identifying details.", "Submit the status enquiry.", "Record the application reference for follow-up."],
        "time": "About 8 minutes",
        "fee": "No fee",
    },
    {
        "id": "SVC-03",
        "name": "Business Licence Check",
        "dept": "Licensing (simulated)",
        "department_id": "DEPT-LIC",
        "category": "Licensing",
        "summary": "Verify whether a sample business licence is active or due for renewal.",
        "description": "Confirm the standing of a business licence in the demonstration register. Results show fictional licence records maintained for testing purposes.",
        "needs": ["Licence or record reference", "Business trading name (sample)", "District of operation"],
        "steps": ["Choose the licence type.", "Enter the reference details.", "Submit the check request.", "Save the confirmation reference."],
        "time": "About 12 minutes",
        "fee": "Fictional processing fee: 5 demo units",
    },
    {
        "id": "SVC-04",
        "name": "Birth Certificate Extract",
        "dept": "Registry (simulated)",
        "department_id": "DEPT-REG",
        "category": "Records",
        "summary": "Request an extract from a registered birth record.",
        "description": "Apply for a certified extract of a birth record from the civil registry. This service provides a demonstration workflow using fictional sample records.",
        "needs": ["Record reference number (TEST-####)", "Full name as registered (sample)", "Collection district"],
        "steps": ["Provide the record reference.", "Confirm the registered details.", "Choose delivery preference (sample).", "Submit and note your reference."],
        "time": "About 15 minutes",
        "fee": "Fictional fee: 2 demo units",
    },
    {
        "id": "SVC-05",
        "name": "Property Tax Certificate",
        "dept": "Revenue (simulated)",
        "department_id": "DEPT-REV",
        "category": "Certificates",
        "summary": "Obtain a statement of property tax standing for a sample parcel.",
        "description": "Request a certificate showing the current tax position for a fictional property holding. Useful for demonstrating clearance and compliance checks.",
        "needs": ["Parcel or record reference", "Registered holder name (sample)", "Assessment district"],
        "steps": ["Enter the parcel reference.", "Confirm holder information.", "Review the tax standing summary.", "Download or note the reference."],
        "time": "About 10 minutes",
        "fee": "No fee",
    },
    {
        "id": "SVC-06",
        "name": "Work Permit Status",
        "dept": "Employment (simulated)",
        "department_id": "DEPT-EMP",
        "category": "Permits",
        "summary": "Check processing status for a sample work permit application.",
        "description": "Track the progress of a fictional work permit request. Status values shown are demonstration data and do not represent real applications.",
        "needs": ["Application reference (ESB-2026-######)", "Applicant sample name", "Contact phone (+256700000###)"],
        "steps": ["Enter your application reference.", "Verify applicant details.", "View the current processing stage.", "Save the status for your records."],
        "time": "About 5 minutes",
        "fee": "No fee",
    },
    {
        "id": "SVC-07",
        "name": "Land Title Search",
        "dept": "Land & Housing (simulated)",
        "department_id": "DEPT-LND",
        "category": "Land",
        "summary": "Search the demonstration land register for a parcel title summary.",
        "description": "View a summary of tenure and registration details for a fictional parcel. This service illustrates how land records may be presented in a portal.",
        "needs": ["Parcel reference", "District name", "Purpose of search"],
        "steps": ["Select the district.", "Enter the parcel reference.", "Review the title summary.", "Record the search reference."],
        "time": "About 12 minutes",
        "fee": "Fictional search fee: 3 demo units",
    },
    {
        "id": "SVC-08",
        "name": "Professional Licence Renewal",
        "dept": "Licensing (simulated)",
        "department_id": "DEPT-LIC",
        "category": "Licensing",
        "summary": "Submit a renewal request for a sample professional licence.",
        "description": "Begin a demonstration renewal for a professional licence record. The form captures sample information and issues a fictional tracking reference.",
        "needs": ["Existing licence reference", "Practitioner sample name", "Renewal category"],
        "steps": ["Confirm your current licence details.", "Choose the renewal period.", "Provide supporting information (sample).", "Submit to receive a reference."],
        "time": "About 20 minutes",
        "fee": "Fictional renewal fee: 8 demo units",
    },
    {
        "id": "SVC-09",
        "name": "Housing Assistance Enquiry",
        "dept": "Land & Housing (simulated)",
        "department_id": "DEPT-LND",
        "category": "Housing",
        "summary": "Register interest in a sample housing assistance programme.",
        "description": "Submit an enquiry about fictional housing assistance options available in demonstration districts. Responses and references are generated for testing only.",
        "needs": ["Household reference or record id", "Current district", "Contact phone (+256700000###)"],
        "steps": ["Describe your housing need (sample).", "Provide household details.", "Select a preferred district.", "Submit the enquiry."],
        "time": "About 15 minutes",
        "fee": "No fee",
    },
]

# Records: keep the exact fields/values for TEST-0001..TEST-0003 as the original
# contract requires (debug exposes TEST-0001). Additional records carry extra
# presentation-only fields.
_BASE_RECORDS = [
    ("Test Citizen One", "ACTIVE"),
    ("Test Citizen Two", "SUSPENDED"),
    ("Test Citizen Three", "ACTIVE"),
]

_FIRST = [
    "Sample", "Demo", "Fictional", "Example", "Placeholder", "Trial", "Mock",
    "Specimen", "Proxy", "Nominal", "Illustrative", "Testcase",
]
_LAST = [
    "Resident", "Applicant", "Holder", "Member", "Participant", "Beneficiary",
    "Citizen", "Client", "Person", "Subject",
]
_DISTRICTS = ["North District", "Central District", "South District", "East District", "West District"]
_PROGRAMMES = ["General", "Community Support", "Civic Services", "Assistance Scheme", "Standard Register"]
_STATUSES = ["ACTIVE", "SUSPENDED", "PENDING", "REVIEW"]


def _name(i: int) -> str:
    # deterministic fictional name
    return f"{_FIRST[(i - 1) % len(_FIRST)]} {_LAST[((i - 1) // len(_FIRST)) % len(_LAST)]} {i:03d}"


def _build_records():
    records = {}
    # 1..3 exact original values (no extra fields)
    for i, (n, s) in enumerate(_BASE_RECORDS, start=1):
        rid = f"TEST-{i:04d}"
        records[rid] = {
            "id": rid,
            "name": n,
            "phone": f"+256700000{i:03d}",
            "national_id": f"CMTEST{i:08d}",
            "pension_status": s,
        }
    # 4..120 deterministic generated records with extra presentation fields
    for i in range(4, 121):
        rid = f"TEST-{i:04d}"
        records[rid] = {
            "id": rid,
            "name": _name(i),
            "phone": f"+256700000{i:03d}",
            "national_id": f"CMTEST{i:08d}",
            "pension_status": _STATUSES[(i - 1) % len(_STATUSES)],
            "district": _DISTRICTS[(i - 1) % len(_DISTRICTS)],
            "programme": _PROGRAMMES[(i - 1) % len(_PROGRAMMES)],
            "last_updated": f"2026-{((i - 1) % 12) + 1:02d}-{((i - 1) % 28) + 1:02d}",
        }
    return records


RECORDS = _build_records()

# The sample_record exposed by /api/v1/admin/debug must remain byte-identical to
# the pre-change payload, so it is the exact original TEST-0001 object (5 fields).
DEBUG_SAMPLE_RECORD = RECORDS["TEST-0001"]

APPLICATIONS = [
    {"reference": "ESB-2026-000123", "service_id": "SVC-01", "service_name": "Citizen Records Lookup", "applicant": "Sample Resident 004", "status": "Received", "submitted": "2026-10-02", "district": "North District"},
    {"reference": "ESB-2026-000124", "service_id": "SVC-02", "service_name": "Pension Benefit Status", "applicant": "Demo Applicant 005", "status": "In review", "submitted": "2026-10-05", "district": "Central District"},
    {"reference": "ESB-2026-000125", "service_id": "SVC-05", "service_name": "Property Tax Certificate", "applicant": "Fictional Holder 006", "status": "Completed", "submitted": "2026-10-09", "district": "South District"},
    {"reference": "ESB-2026-000126", "service_id": "SVC-07", "service_name": "Land Title Search", "applicant": "Example Member 007", "status": "Awaiting information", "submitted": "2026-10-12", "district": "East District"},
    {"reference": "ESB-2026-000127", "service_id": "SVC-03", "service_name": "Business Licence Check", "applicant": "Placeholder Participant 008", "status": "Received", "submitted": "2026-10-15", "district": "West District"},
    {"reference": "ESB-2026-000128", "service_id": "SVC-06", "service_name": "Work Permit Status", "applicant": "Trial Beneficiary 009", "status": "In review", "submitted": "2026-10-18", "district": "North District"},
]

NOTICES = [
    {"id": "NTC-01", "date": "2026-10-20", "title": "Scheduled maintenance window", "summary": "The demonstration portal will be unavailable for routine maintenance on 2026-10-25 between 01:00 and 03:00 (demo time).", "body": "This is a fictional maintenance notice for the eServices demonstration environment. No real services are affected."},
    {"id": "NTC-02", "date": "2026-10-14", "title": "New online licence renewal form", "summary": "A sample renewal workflow is now available for selected professional licences in this demo portal.", "body": "Applicants can try the demonstration renewal steps under Licensing services. All references and outcomes are fictional."},
    {"id": "NTC-03", "date": "2026-10-08", "title": "Updated record lookup guidance", "summary": "Guidance for using the citizen records lookup service has been refreshed with clearer steps.", "body": "Visit the Help Centre for the latest sample instructions. The records shown are generated test data only."},
    {"id": "NTC-04", "date": "2026-09-30", "title": "Quarterly demonstration data refresh", "summary": "Sample records and application references have been rotated as part of the regular demo refresh.", "body": "Record identifiers continue to follow the TEST-#### convention. No personal or production data is used."},
]

FAQ = [
    {"q": "Is this a real government website?", "a": "No. This is a demonstration site using fictional data only. It exists to support testing and evaluation and must not be treated as a live service."},
    {"q": "What information do I need for a records lookup?", "a": "You need a record reference in the form TEST-#### and the demonstration API key when using the protected records lookup page."},
    {"q": "Why does the records lookup ask for an API key?", "a": "The underlying records endpoint is protected. The portal asks you to provide the key so access is explicit rather than embedded in the page."},
    {"q": "Are the people and addresses shown real?", "a": "No. All names, phone numbers, identifiers, references and addresses are fictional and follow the project's demonstration conventions."},
    {"q": "How do I track a sample application?", "a": "Open the Applications area to view sample references and statuses, or submit a new sample request to receive a fictional tracking reference."},
    {"q": "Who can I contact for support?", "a": "For this demonstration environment, use the Help Centre on this site. No real contact channels or personal assistance are provided."},
]

# Application reference counter seed (deterministic within process; starts after samples)
_NEXT_APP_NUM = 129


def next_application_ref():
    global _NEXT_APP_NUM
    ref = f"ESB-2026-{_NEXT_APP_NUM:06d}"
    _NEXT_APP_NUM += 1
    return ref


def get_service(sid):
    for s in SERVICES:
        if s["id"] == sid:
            return s
    return None


def get_application(ref):
    for a in APPLICATIONS:
        if a["reference"] == ref:
            return a
    return None
