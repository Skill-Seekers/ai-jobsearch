#!/usr/bin/env python3
"""Build the fictional sample workspace used by the demo and the tests. Standard library only.

  python examples/build_sample_workspace.py [DEST]        (default: examples/sample-workspace)

Everything here is invented: the candidate (Alex Rivera), the employers (Contoso, Fabrikam, ...), the postings, the
numbers. Posting links use ids that start 0000 so they can never be mistaken for real ones. Dates are fixed so a run is
reproducible: the sample "today" is 2026-10-26."""
import json, os, sys, zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = '2026-10-26'
SKIP_IF_EXISTS = ('jobsearch.config.json',)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, indent=1, ensure_ascii=False) + '\n')


def make_docx(path, paragraphs):
    """paragraphs: list of (style, text) with style 'h' (bold heading) or 'p'. Minimal valid .docx, no images, no tables."""
    body = []
    for style, text in paragraphs:
        rpr = '<w:rPr><w:b/></w:rPr>' if style == 'h' else ''
        body.append('<w:p><w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (rpr, escape(text)))
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document %s><w:body>%s</w:body></w:document>' % (ns, ''.join(body))
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>Sample Candidate</dc:creator><dc:title>Sample resume (fictional)</dc:title></cp:coreProperties>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('word/document.xml', doc); z.writestr('docProps/core.xml', core)


RESUME = [
    ('h', 'Alex Rivera'),
    ('p', 'Senior Technical Program Manager | Austin, TX | alex.rivera@example.com | 512-555-0100'),
    ('h', 'Summary'),
    ('p', 'Technical program manager with 12 years in silicon and hardware product launches. Leads cross-functional teams from bring-up through customer qualification and volume production. Sample resume: all content is fictional.'),
    ('h', 'Experience'),
    ('p', 'Senior Technical Program Manager, Northwind Networks (2019 to present)'),
    ('p', 'Led NPI for a 12-person cross-functional team across firmware, hardware and test; shipped 4 platform releases on schedule (sample figure).'),
    ('p', 'Ran customer qualification for two OEM accounts; cut qualification cycle time by 18 percent (sample figure).'),
    ('p', 'Owned risk and dependency tracking in Jira and Confluence; escalated blockers to directors weekly.'),
    ('p', 'Technical Program Manager, Litware Storage (2014 to 2019)'),
    ('p', 'Managed bring-up and post-silicon validation for a storage controller; coordinated suppliers and manufacturing ramp.'),
    ('p', 'Built the program dashboard in Excel and SQL that leadership used for monthly reviews.'),
    ('h', 'Education'),
    ('p', 'B.S. Electrical Engineering, State University (sample)'),
    ('h', 'Skills'),
    ('p', 'NPI, ASIC and SoC programs, bring-up, qualification, firmware, hardware, program management, risk management, stakeholder management, Jira, Confluence, Excel, SQL, Python, agile'),
]

METRICS = """# Metrics worksheet (fictional sample)

Every number on a resume or letter must come from this file or the master resume, verbatim. Nothing else may be used.

| ID | Employer | Claim | Number | Source / evidence |
|----|----------|-------|--------|-------------------|
| M1 | Northwind Networks | Platform releases shipped on schedule | 4 | sample project plan |
| M2 | Northwind Networks | Team size led | 12 | sample org chart |
| M3 | Northwind Networks | Customer qualification cycle time reduction | 18% | sample qualification log |

## Decided not to claim
- PMP: not certified.
- Six Sigma Black Belt: no belt held; only Lean practices are claimed.
"""

JD = """COMPANY: Contoso Semiconductor
TITLE: Senior Technical Program Manager, Silicon Bring-up
SOURCE: Sample
POSTED: 2026-10-25
=====================================================================
Contoso Semiconductor is hiring a Senior Technical Program Manager to lead silicon bring-up and customer qualification for a new ASIC family.

What you will do
- Own the program plan from tape-out through post-silicon validation, bring-up, qualification and volume production.
- Drive cross-functional execution across hardware, firmware, test and manufacturing; manage risk, dependencies and escalations.
- Run customer qualification with OEM and ODM partners and report status to executive stakeholders.

Requirements
- 8+ years of technical program management in semiconductor or hardware.
- Experience with NPI, ASIC or SoC programs, firmware and hardware bring-up.
- Strong stakeholder management; Jira and Confluence; SQL or Python for dashboards.
- PMP or equivalent is a plus. Six Sigma or Lean experience is a plus.
"""

DESC = dict(
    silicon=('Lead silicon bring-up, post-silicon validation and customer qualification for a new ASIC. Own NPI from tape-out to volume production across hardware, firmware and test. '
             'Manage risk, dependencies and executive stakeholders. Requirements: 8+ years of technical program management in semiconductor or hardware; OEM and ODM customer programs.'),
    customer=('Lead customer-facing program delivery for OEM and hyperscale customers: qualification, design-in, escalations and launch readiness for a new SoC platform. '
              'Requirements: 7+ years of technical program management; hardware and firmware NPI experience.'),
    network=('Own NPI for next-generation networking hardware: ASIC bring-up, board and firmware integration, qualification with OEM partners and volume production ramp. '
             'Requirements: 10+ years of program management; Ethernet or optical interconnect background.'),
    cloud=('Drive data center server and rack capacity programs for a cloud platform: hardware qualification, supplier coordination and hyperscale deployment schedules. '
           'Requirements: 7+ years technical program management; data center hardware experience.'),
    storage=('Lead storage platform programs: SSD and controller firmware, NAND qualification, customer acceptance and volume production. Requirements: 6+ years of technical program management.'),
    device=('Run device launch programs from NPI to launch: hardware, firmware, supply chain and customer acceptance. Requirements: 6+ years of program management.'),
    ml=('Run ML platform and model training programs: model release, inference serving stack, machine learning pipeline delivery and LLM evaluation. Requirements: 6+ years of program management; generative ai platform experience.'),
    generic=('Lead cross-functional technical programs for hardware products: schedules, risks, stakeholders, launch readiness. Requirements: 6+ years of technical program management.'),
)


def row(src, company, title, location, posted, link, desc, salary='', apps=0, emp='Full-time', level='Mid-Senior level'):
    return {'_source': src, 'companyName': company, 'title': title, 'location': location, 'postedAt': posted, 'link': link, 'descriptionText': desc,
            'salary': salary, 'applicantsCount': apps, 'employmentType': emp, 'seniorityLevel': level}


def raw_rows():
    L = 'https://www.linkedin.com/jobs/view/%s-%s'
    I = 'https://www.indeed.com/viewjob?jk=%s'
    return {
        'linkedin_groupA.json': [
            row('LinkedIn', 'Contoso Semiconductor', 'Senior Technical Program Manager, Silicon Bring-up', 'Austin, TX', '2026-10-25', L % ('senior-tpm-silicon', '0000000101'), DESC['silicon'], '$185,000 - $240,000', 22),
            row('LinkedIn', 'Fabrikam Silicon', 'Staff Technical Program Manager, Customer Programs', 'Remote (United States)', '2026-10-24', L % ('staff-tpm-customer', '0000000102'), DESC['customer'], '', 41),
            row('LinkedIn', 'Wingtip Devices', 'Senior Technical Program Manager, Hardware', 'Austin, TX', '2026-10-23', L % ('senior-tpm-hardware', '0000000103'), DESC['generic'], '$175,000 - $205,000', 17),
            row('LinkedIn', 'Proseware Labs', 'Senior Technical Program Manager, ML Model Training', 'Austin, TX', '2026-10-24', L % ('senior-tpm-ml', '0000000104'), DESC['ml'], '$190,000 - $250,000', 63),
            row('LinkedIn', 'Contoso Semiconductor', 'Scrum Master', 'Austin, TX', '2026-10-25', L % ('scrum-master', '0000000105'), DESC['generic'], '', 9),
            row('LinkedIn', 'Fabrikam Silicon', 'Senior Technical Program Manager', 'Boston, MA', '2026-10-25', L % ('senior-tpm-boston', '0000000106'), DESC['silicon'], '$180,000 - $230,000', 12),
        ],
        'linkedin_B1.json': [
            row('LinkedIn', 'Northwind Networks', 'Principal Technical Program Manager, Networking', 'Austin, TX', '2026-10-23', L % ('principal-tpm-networking', '0000000201'), DESC['network'], '$200,000 - $260,000', 30),
            row('LinkedIn', 'Tailspin Cloud', 'Senior Technical Program Manager, Cloud Infrastructure', 'Austin, TX (Hybrid)', '2026-10-22', L % ('senior-tpm-cloud', '0000000202'), DESC['cloud'], '$170,000 - $220,000', 54),
            row('LinkedIn', 'Litware Storage', 'Technical Program Manager, Storage Platforms', 'Round Rock, TX', '2026-10-26', L % ('tpm-storage', '0000000203'), DESC['storage'], '$160,000 - $190,000', 5),
            row('LinkedIn', 'Litware Storage', 'Senior Technical Program Manager, Controller Firmware', 'Austin, TX', '2026-10-22', L % ('senior-tpm-firmware', '0000000204'),
                DESC['storage'] + ' This position has been filled.', '$175,000 - $210,000', 88),
            row('LinkedIn', 'Fabrikam Silicon', 'Senior Technical Program Manager, Quality', 'Austin, TX', '2026-10-22', L % ('senior-tpm-quality', '0000000205'),
                DESC['silicon'] + ' Apply by Oct 20, 2026.', '', 14),
            row('LinkedIn', 'Tailspin Cloud', 'Technical Program Manager', 'Austin, TX', '2026-10-25', L % ('tpm-entry', '0000000206'), DESC['generic'], '$90,000 - $110,000', 70),
            row('LinkedIn', 'Contoso Semiconductor', 'Senior Technical Program Manager, Legacy Parts', 'Austin, TX', '2026-10-01', L % ('senior-tpm-legacy', '0000000207'), DESC['silicon'], '', 140),
            row('LinkedIn', 'Adventure Works Devices', 'Senior Program Manager, Device Launch', 'Remote (United States)', '2026-10-21', L % ('senior-pm-device', '0000000208'), DESC['device'], '', 77),
        ],
        'indeed.json': [
            row('Indeed', 'Contoso Semiconductor', 'Senior Technical Program Manager, Silicon Bring-up', 'Austin, TX', '2026-10-25', I % '0000000000a1b2c3', DESC['silicon'], '$185,000 - $240,000'),
            row('Indeed', 'Globex Corporation', 'Senior Technical Program Manager', 'Austin, TX', '2026-10-24', I % '0000000000d4e5f6', DESC['generic'], '$200,000 - $240,000'),
            row('Indeed', 'Initech Holdings', 'Staff Technical Program Manager', 'Austin, TX', '2026-10-24', I % '0000000000a7b8c9', DESC['generic'], ''),
            row('Indeed', 'Robert Half', 'Technical Program Manager (contract)', 'Austin, TX', '2026-10-25', I % '0000000000c1d2e3', DESC['generic'], ''),
        ],
        'glassdoor.json': [
            row('Glassdoor', 'Tailspin Cloud', 'Senior Technical Program Manager, Cloud Infrastructure', 'Austin, TX', '2026-10-22', 'https://www.glassdoor.com/job-listing/0000000301', DESC['cloud'], '$170,000 - $220,000'),
        ],
    }


def tracker():
    return {'schema_version': '1.2', 'applications': [
        {'id': 'litware-storage-tpm', 'company': 'Litware Storage', 'title': 'Senior Technical Program Manager, Controller Firmware', 'req_id': None, 'source_job_id': '0000000204',
         'jd_file': 'resume/job_descriptions/litware-storage_tpm-firmware.txt', 'folder': 'Litware-Storage-TPM', 'title_keywords': ['controller', 'firmware'], 'status': 'drafted',
         'applied': False, 'applied_date': None, 'tailored_date': '2026-10-07', 'outcome': None, 'notes': 'Sample entry: package built, submission not confirmed.'},
        {'id': 'tailspin-cloud-tpm', 'company': 'Tailspin Cloud', 'title': 'Senior Technical Program Manager, Cloud Infrastructure', 'req_id': None, 'source_job_id': None,
         'jd_file': None, 'folder': None, 'title_keywords': ['cloud', 'infrastructure'], 'status': 'applied', 'applied': True, 'applied_date': '2026-10-24', 'tailored_date': '2026-10-23',
         'outcome': None, 'notes': 'Sample entry: the candidate confirmed this submission.'},
        {'id': 'adventure-works-pm', 'company': 'Adventure Works Devices', 'title': 'Program Manager, Launch', 'req_id': None, 'source_job_id': None, 'jd_file': None, 'folder': None,
         'title_keywords': ['launch'], 'status': 'passed', 'applied': False, 'applied_date': None, 'tailored_date': '2026-09-15', 'outcome': 'closed', 'notes': 'Posting closed.'}]}


def build(dest):
    dest = os.path.abspath(dest)
    make_docx(os.path.join(dest, 'resume', 'master', 'ARivera_v1.0.docx'), RESUME)
    write(os.path.join(dest, 'resume', 'metrics-worksheet.md'), METRICS)
    write(os.path.join(dest, 'resume', 'job_descriptions', 'contoso_senior-tpm-silicon-bringup.txt'), JD)
    write(os.path.join(dest, 'resume', 'job_descriptions', 'litware-storage_tpm-firmware.txt'), JD.replace('Contoso Semiconductor', 'Litware Storage').replace('Silicon Bring-up', 'Controller Firmware'))
    write_json(os.path.join(dest, 'tracking', 'applied_tracking.json'), tracker())
    for name, rows in raw_rows().items():
        write_json(os.path.join(dest, 'search', 'raw', '2026-10-26', name), rows)
    write_json(os.path.join(dest, 'search', 'raw', 'adjustments.example.json'), [
        {'company': 'Contoso', 'title_contains': 'Bring-up', 'delta': 2, 'reason': 'Example: description names a program owned end to end, which the keyword scorer cannot see.'}])
    return dest


if __name__ == '__main__':
    d = build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sample-workspace'))
    print('built sample workspace at', d)
