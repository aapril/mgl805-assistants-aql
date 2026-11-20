# Architecture of the library service

The service follows a layered architecture.

- `library.api` (presentation) receives HTTP requests, validates them, and calls the services. It never accesses the database directly.
- `library.services` (application) implements the use cases: catalog, loans, notifications.
- `library.domain` holds the business entities (books, loans). It depends on nothing else in the service, so that the business rules can be tested without a database.
- `library.infrastructure` accesses the database and sends e-mail.

The team considers the code "ready" when the quality gates of `debt_rules.json` are met and a person from the quality assurance group approves the report.
