# Business scenario

RelayCart is a fictional B2B SaaS serving merchants such as Acme Bikes and Ocean Apparel. A shopper checks out on Acme Bikes' website; RelayCart's `checkout-api` creates the order behind that experience. Acme Bikes pays RelayCart for its subscription. The local `customers`, `subscriptions`, and `customer_service_subscriptions` records distinguish merchants that use checkout from those that use only billing or notifications. This distinction will matter when later automation identifies affected merchants.

Acme Bikes is an Enterprise checkout customer, Ocean Apparel is on Growth, and Green Dental is a Starter account using only notifications. All three are invented.

An operator confirms checkout works and deploys v1.8.2. The deployment operation completes successfully. A later `/health` probe independently discovers the application compatibility failure, and a synthetic checkout independently fails and records a `checkout.failed` event. The event log distinguishes `deployment.completed`, `health.failed`, and `checkout.failed`; repeated health polls do not duplicate the health event for that deployment. The operator then manually rolls back and reads back a successful order. Deployment completion does not mean the application is healthy, and application health does not guarantee that a business transaction succeeds. The scenario demonstrates operational evidence and recovery. It does not automatically detect or declare an incident, notify customers, or send messages. Billing and notification APIs provide historical context only; they are not separate running services in Phase 1.

`GET /customers` exports synthetic merchant slug, company, plan, contact, and service associations as JSON. It is a local mapping surface for a later GoHighLevel phase; Phase 1 performs no GoHighLevel writes.

All merchant, order, metric, and service data is synthetic. The demo does not send messages or change any real service, order, or account. There are no external integrations in Phase 1.
