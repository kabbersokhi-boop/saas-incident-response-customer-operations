# GoHighLevel data model

The isolated location contains 30 mapped, synthetic RelayCart customer contacts (`@example.test`). Each carries its existing RelayCart customer key, company, plan, and demo marker. `ghl_contacts` maps the immutable RelayCart slug to a real GHL contact ID. Re-running `scripts/ghl-provision seed` verifies the remote ID and email and does not duplicate contacts.

`Service Case` is a real GHL Custom Object, key `custom_objects.relaycart_service_case`. Its primary display field is Case Key. Additional fields are Incident ID, RelayCart Customer Key, Service, Severity, Impact Summary, Technical Status, Customer Status, Affected Since, Last Technical Update, Recovery Verified At, Customer Confirmed At, Sync Revision, and Demo Record. The real Contact ↔ Service Case association is `relaycart_affected_customer`, ID `6abb11b64427829e84164de5`, shown as an affected-customer relationship in HighLevel. A text contact ID is not used as a substitute for the relationship.

One incident/customer pair has one deterministic key, `SC-<incident-id>-<customer-key>`, and one unique effect ID, `service-case:<incident-id>:<customer-key>`. The local `ghl_effects` ledger stores remote case IDs and retry state. The separate `ghl_customer_feedback` table stores outcomes without modifying `ir_incidents`.

Technical Status is copied from the technical incident. Customer Status starts `AWAITING_RECOVERY`, becomes `AWAITING_CONFIRMATION` only after native technical-recovery handoff, and ends `CONFIRMED_RESOLVED` or `NEEDS_FOLLOW_UP` only after a customer outcome. Silence or ambiguity leaves it pending. In particular, `Technical Status=RECOVERED` never automatically implies `Customer Status=CONFIRMED_RESOLVED`.

Contacts are selected from RelayCart's active service subscriptions, not all GHL contacts. `checkout-api` has 18 subscribed customers, including Acme Bikes and Ocean Apparel. Green Dental is not subscribed and receives no case for a checkout incident.
