# ADR-0018: Store basin results server-side under a UUID-validated id with a 24-hour expiry

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** [ADR-0015](0015-store-basin-results-server-side-under-a-random-id-with-a-24-hour-expiry.md)
- **Related change:** openspec/changes/add-basin-extraction/ (design D1)

## Context

ADR-0015 stores basin results as `<id>.json` under a random id and expires them after 24 hours.
It checks ids only against `^[0-9a-f]{32}$`, and its message for a missing result gives the user
no way back. Planning review raised two points:

- **Security**: the id comes from the URL and becomes part of a file path. Any request carrying
  a value that cannot be one of our ids (a path traversal such as `../../pyproject.toml`, an
  uppercase or hyphenated form, an arbitrary string) must be rejected before any path is built
  and without any file-system call, not only kept inside the store directory.
- **Usability**: links expire after 24 hours by design, so reaching an expired result is
  normal. The page must say what happened and link straight to the basin form.

The other forces of ADR-0015 are unchanged: a polygon cannot travel in a URL, re-reading the
box per request costs seconds, uploads are user data, and there is no database (ADR-0002).

## Options considered

1. **Keep ADR-0015 and add a UUIDv4 check plus the new message**: same storage. Ids are
   validated as the canonical form of a version-4 UUID, and every rejection looks the same to
   the user. Pros: strict whitelist, no disk access for invalid input, a clear way back.
2. **Keep the 32-hex regex only**: simpler. Cons: it accepts values that `uuid4()` never
   produces, and the rule does not say that rejection happens before any file-system call.
3. **Resolve the path and check that it stays inside the store** (`Path.resolve()` plus
   `is_relative_to`): a common defense. Cons: it touches the disk (resolving symlinks) to
   reject input that a whitelist rejects for free, and it depends on how the platform handles
   paths.
4. **Separate messages for unknown and expired ids**: more precise. Cons: deleted files cannot
   be told apart from ids that never existed, and probing ids would reveal which ones did.

The storage alternatives rejected by ADR-0015 (stateless URL with an encoded mask, everything in
the POST response, an in-memory cache) remain rejected for the same reasons.

## Decision

We will use option 1. Every ADR-0015 rule stays the same, except the id rule and the message:

- `POST /basin` validates the request, reads the bounding box once (ADR-0017), computes the
  result (ADR-0016) and saves it as `<id>.json` in `BASIN_STORE_DIR`. The default is
  `uploads/basins/`, which is gitignored. The POST then redirects (303) to
  `/basin/result/<id>`.
- `<id>` is `uuid4().hex`.
- **Id validation**: a value is a result id only if it is the 32-character lowercase
  hexadecimal form of a version-4 UUID. That means it matches
  `^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$` and `uuid.UUID(value).hex == value`. Routes and
  the store run this check first. Any other value returns 404 before a `Path` is built and
  without any file-system call.
- **Missing result**: an unknown, expired or invalid id gets the same 404 page, saying "This
  result has expired; upload the basin again", with a link to `/basin`. Chart and download
  URLs return a plain 404 and no file.
- The stored file holds the dissolved WGS84 geometry, the basin file name (base name only), the
  feature count, the area, the centroid, the cells, the years, the period and the areal series.
  The uploaded file is never stored.
- Writes are atomic: a temporary file, then `os.replace`. Results older than `BASIN_TTL_HOURS`
  (default 24, judged by modification time) are deleted at startup, before each save, and when
  a load finds them expired.
- ADR-0013 stays in force for point results.

Rejected: the regex alone (option 2), because it is a looser whitelist and does not promise
that invalid input never reaches the disk. Rejected: resolving the path (option 3), because it
touches the disk for input that can be rejected without it; the whitelist makes it
unnecessary. Rejected: separate messages (option 4), because the cases cannot be told apart
reliably and probing would reveal which ids existed.

## Consequences

- **Positive:** input from the URL can never name a file outside the store, and invalid input
  never reaches the disk. Expired links lead straight back to the form. The other benefits of
  ADR-0015 (one NetCDF pass, the exact polygon, self-cleaning storage) remain.
- **Negative / trade-offs:** the same as ADR-0015. There is state on disk, links expire after
  24 hours, and several hosts would need a shared directory. Ids produced by any other UUID
  version or format are rejected.
- **Follow-up:** `basin-extraction` spec (result URL, storage and expiry). `/adr-review` checks
  that every basin route validates the id before calling the store, that the store validates
  it again before building a path, and that `uploads/` stays gitignored.
