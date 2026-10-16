# React frontend

Reconstructed from the user-provided implementation brief; original file was absent.

React Router pages: /, /jobs, /jobs/:id, /recommended, /profile, /resume, /applications, /tpo, /mlops and /admin plus health display. TanStack Query handles server state and invalidation. Tailwind CSS styles a responsive accessible dashboard with semantic labels, focus states and clear loading/error/empty states. Configure local API token through a session-only settings form. Render job descriptions as text; never inject ATS HTML.

Completion adds /saved and /system, protected resume history and deletion, persistent bookmark state, URL-backed search filters, application status/search filters, saved-evaluation export, linked duplicate review and cache-clearing access changes. See UI_FEATURE_GUIDE.md for page-by-page behavior and browser verification.
