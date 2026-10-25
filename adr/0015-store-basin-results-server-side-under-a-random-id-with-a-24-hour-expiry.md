# ADR-0015: Store basin results server-side under a random id with a 24-hour expiry

- **Status:** Superseded by [ADR-0018](0018-store-basin-results-server-side-under-a-uuid-validated-id-with-a-24-hour-expiry.md)
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/add-basin-extraction/ (design D1)

## Context

Point results use stateless GET URLs: the query string describes the whole result, and each
page, chart and download re-reads one cell (ADR-0013). A basin result cannot work that way:

- The input is an uploaded polygon (GeoJSON or zipped Shapefile, up to 10 MB). It cannot travel
  in a URL. Even an encoded cell mask plus a simplified outline takes several KB, close to the
  16 KB request-line limit of h11, and the outline drawn on the map would no longer be the
  user's own.
- A result view sends up to 6 requests (the page and 5 charts), plus 5 downloads. Measured on
  the real daily file, a full-period read of a 30 × 30-cell box takes 1.55 s cold, against
  about 0.15 s for one cell. Re-reading the box for each request would cost seconds per image.
- Uploaded basins are user data. They must never reach git, and any temporary copy must be
  removed.
- The app has no database (ADR-0002).

## Options considered

1. **Server-side JSON result under a random id, with expiry**: the POST computes the result
   once and writes it to one file. Later requests load that file.
2. **Stateless URL with an encoded cell mask and outline**: no server state and permanent
   links. Cons: each request re-reads the box, URLs are long and close to the limit, the outline
   is simplified, and the area and notices can be edited in the URL.
3. **Everything in the POST response**: inline base64 charts and data-URI downloads. No state.
   Cons: the page weighs several MB, there is no pagination and no bookmark, and any change
   needs a new upload. ADR-0013 already rejected inline base64.
4. **In-memory cache keyed by id**: fast, but it grows the process toward its ~300 MB memory
   limit, it is lost on restart, and it is not shared between workers.

## Decision

We will use option 1:

- `POST /basin` validates the request, reads the basin's bounding box once (ADR-0017), computes
  the result (ADR-0016) and saves it as `<id>.json` in `BASIN_STORE_DIR`. The default is
  `uploads/basins/`, which is gitignored. The POST then redirects (303) to
  `/basin/result/<id>`.
- `<id>` is `uuid4().hex`: 32 lowercase hexadecimal characters and 122 random bits. Every id is
  checked against `^[0-9a-f]{32}$` before a path is built from it.
- The file stores the dissolved WGS84 geometry, the basin file name (base name only), the
  feature count, the area, the centroid, the cells and their status, the years, the period and
  the areal series. **The uploaded file is never stored**: it is parsed in memory.
- Pages, charts (`/basin/result/<id>/chart/<kind>.png`) and downloads
  (`/basin/result/<id>/export/...`) load the stored result and never read NetCDF.
- Writes are atomic: a temporary file in the same directory, then `os.replace`.
- **Expiry**: results older than `BASIN_TTL_HOURS` (default 24) are deleted at startup and
  before each save, judged by the file modification time. Loading an expired result deletes it.
  An unknown, expired or malformed id returns 404 with "This basin result has expired or does
  not exist. Upload the basin again."
- ADR-0013 stays in force for point results. This decision covers basin results only.

Rejected: stateless URL (option 2), because of repeated box reads, URL length, simplified
outlines and editable values. Rejected: inline response (option 3), because there is no
pagination or bookmark and pages weigh several MB. Rejected: in-memory cache (option 4),
because of the memory limit, loss on restart and no sharing between workers.

## Consequences

- **Positive:** one NetCDF pass per basin request. Fast pages, charts and downloads. The map
  shows the exact polygon. No user upload is kept, and stored results clean themselves up.
- **Negative / trade-offs:** the server keeps state on disk. Links stop working after 24 hours
  or when the store is wiped. A deployment on several hosts would need a shared directory.
  Each result takes about 0.3 MB of disk while it lives.
- **Follow-up:** `basin-extraction` spec (result URL, storage and expiry). `/adr-review` checks
  that `uploads/` stays gitignored and that no route opens a store path without checking the
  id. Making links permanent or moving to a database requires superseding this ADR.
