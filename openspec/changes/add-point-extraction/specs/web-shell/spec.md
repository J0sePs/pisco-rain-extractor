# Spec Delta

## MODIFIED Requirements

### Requirement: Shared layout
Every HTML page SHALL use the same layout: a header with the application name, a
navigation bar with links to `/`, `/point` and `/dataset` (marking the current page), and a
footer crediting SENAMHI as the data owner.

#### Scenario: Navigation on the dataset page
- **WHEN** a user opens `GET /dataset`
- **THEN** the page contains the header, navigation links to `/`, `/point` and `/dataset`, and the footer
- **AND** the `/dataset` link is marked as the current page

#### Scenario: Navigation on the point page
- **WHEN** a user opens `GET /point`
- **THEN** the navigation contains links to `/`, `/point` and `/dataset`
- **AND** the `/point` link is marked as the current page

#### Scenario: Unknown page
- **WHEN** a user opens `GET /does-not-exist`
- **THEN** the response status is 404
