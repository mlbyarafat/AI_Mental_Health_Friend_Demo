
# Safety Policy (Demo Summary)

- This demo provides *supportive* content only and **is not** a replacement for clinical care.
- High-risk messages detected by keyword rules will trigger a safety template and advise the user to contact local emergency services.
- Data export and deletion endpoints included; deletion redacts PII and user content in DB but does not securely wipe backups.
- For production: replace base64 with proper encryption, add audit logs, KMS-backed keys, clinician review sign-off, and legal compliance per region.
