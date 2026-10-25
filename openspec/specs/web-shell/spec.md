# web-shell Specification

## Purpose

Provides the server-rendered frame every page shares: home page, common layout with
navigation, and local static assets, working without JavaScript or external resources.

## Requirements

### Requirement: Home page
`GET /` SHALL respond 200 with an HTML page that names the application, states that the
data source is SENAMHI PISCOp v3.0, and links to the dataset page.

#### Scenario: Open home page
- **WHEN** a user opens `GET /`
- **THEN** the response status is 200 with content type `text/html`
- **AND** the page contains "pisco-rain-extractor", "PISCOp v3.0", "SENAMHI" and a link to `/dataset`

#### Scenario: Home page without data
- **GIVEN** `DATA_DIR` contains no PISCOp files
- **WHEN** a user opens `GET /`
- **THEN** the response status is 200

### Requirement: Shared layout
Every HTML page SHALL use the same layout: a header with the application name, a
navigation bar with links to `/`, `/point`, `/basin` and `/dataset` (marking the current
page), and a footer crediting SENAMHI as the data owner.

#### Scenario: Navigation on the dataset page
- **WHEN** a user opens `GET /dataset`
- **THEN** the page contains the header, navigation links to `/`, `/point`, `/basin` and
  `/dataset`, and the footer
- **AND** the `/dataset` link is marked as the current page

#### Scenario: Navigation on the point page
- **WHEN** a user opens `GET /point`
- **THEN** the navigation contains links to `/`, `/point`, `/basin` and `/dataset`
- **AND** the `/point` link is marked as the current page

#### Scenario: Navigation on the basin page
- **WHEN** a user opens `GET /basin`
- **THEN** the navigation contains links to `/`, `/point`, `/basin` and `/dataset`
- **AND** the `/basin` link is marked as the current page

#### Scenario: Unknown page
- **WHEN** a user opens `GET /does-not-exist`
- **THEN** the response status is 404

### Requirement: Local static assets only
Pages SHALL load styles only from `/static/` on the same server, SHALL NOT reference
external URLs for CSS, fonts or scripts, and SHALL NOT include JavaScript.

#### Scenario: Stylesheet served locally
- **WHEN** a user opens `GET /`
- **THEN** the page links a stylesheet under `/static/`
- **AND** `GET` on that stylesheet responds 200 with content type `text/css`

#### Scenario: No external resources or scripts
- **WHEN** a user opens `GET /` or `GET /dataset`
- **THEN** the HTML contains no `<script>` element and no `http://` or `https://` URL in
  `href` or `src` attributes of `link`, `script` or `img` elements

#### Scenario: Missing static file
- **WHEN** a user requests `GET /static/missing.css`
- **THEN** the response status is 404
