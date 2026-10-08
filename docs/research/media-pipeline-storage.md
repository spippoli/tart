# Research: media pipeline and storage within budget

- Ticket: [#10](https://github.com/spippoli/tart/issues/10) (part of the MVP specification map, [#2](https://github.com/spippoli/tart/issues/2))
- Date: 2026-10-08
- Status: research input. This file makes **no decision**. The choice belongs to the "Tech stack decision" ticket.

## Question

How should images and PDFs be stored and processed for a self-hostable instance within €20/month? The ticket asks about:

- S3-compatible storage options (MinIO, Garage, managed equivalents)
- derivative generation (thumbnails, web sizes, PDF first-page previews)
- EXIF/GPS stripping
- upload validation and size limits
- where processing runs (synchronously, or in a worker queue alongside FastAPI)
- storage growth estimates

## Constraints from the map and the domain

- **Stack (decided)**: FastAPI with PostgreSQL/PostGIS. The reference deployment is a self-hostable Docker Compose stack with **adapters for DB and storage**, so managed equivalents can be swapped in. Rome runs on at most €20/month ([#2](https://github.com/spippoli/tart/issues/2)).
- **Media kinds**: images, PDFs, text and links. Video and audio are out of scope. Only images and PDFs produce binary files. Text and links are database rows.
- **Documentation item** (`GLOSSARY.md`): an independent piece of evidence, dated by its *Observed date*. An image shows a single Location.
- **Withdrawal** (`GLOSSARY.md`): hiding a Documentation item from the public for legal, rights or privacy reasons. The file is not deleted, but it must stop being publicly reachable.
- **Submissions are not archive records** (ADR 0002). Media attached to a pending Submission must not be publicly served as if it were accepted.
- **The artwork location is not the submitter's location** (`CLAUDE.md`). GPS metadata in a photo is personal data about the contributor. It may also be useful evidence of the artwork's position.

## 1. Storage options

### 1.1 Self-hosted S3-compatible servers (status as of 2026-10-08)

| Option | License | Status / maturity | Single-node | S3 gaps relevant to TART |
|---|---|---|---|---|
| **MinIO (community)** | AGPLv3 | **Unmaintained.** The repo was archived on 2026-04-25. The README says "THIS REPOSITORY IS NO LONGER MAINTAINED" and that the community edition is "distributed as source code only", with no pre-compiled binaries or maintained images. It points users to the commercial "AIStor" products. [1] | Yes | n/a (not recommended) |
| **Garage** | AGPLv3 [2] | Active. The current docs use image `dxflrs/garage:v2.4.1`. Designed for small, geo-distributed self-hosting. Minimum 1 GB RAM and 16 GB disk. [3][4] | Yes (`replication_factor = 1`, `--single-node`). The docs warn that this provides no redundancy. [4] | No versioning, no object lock, no bucket policies or ACLs (it uses per-key, per-bucket permissions instead). Presigned URLs, multipart uploads and CORS are supported. Lifecycle support is partial. [5] |
| **SeaweedFS** | Apache-2.0 (an Enterprise edition also exists) | Active. `weed mini` is described as "fine for single-node production". [6] | Yes | Broad S3 coverage, including versioning, object lock, lifecycle, presigned URLs and SSE. [6] |
| **RustFS** | Apache-2.0 ("RustFS" is a trademark of RustFS, Inc.) | Young. The README mentions `1.0.0-beta.11`, and some features are "Preview". The default console credentials are `rustfsadmin/rustfsadmin`. [7] | Yes, but a single-drive deployment cannot be expanded in place. [7] | Not evaluated in depth |
| **Local filesystem (no S3)** | n/a | A Docker volume on the VPS disk, served through the app or a reverse proxy | Yes | Not S3. It needs its own storage adapter implementation. |

Notes:

- **AGPLv3 and TART's licence.** Garage and MinIO are AGPLv3. If TART runs them unmodified as separate containers, this is unlikely to affect TART's own licence, but this is not legal advice. It should be noted in the Licensing Decision Record (LDR). Modifying them and offering them over a network triggers source-sharing obligations [2].
- **The hidden cost of self-hosted object storage on a single VPS.** It runs on the same disk as the database, so it adds operational surface without adding durability. Its real value is **API parity** with managed S3: a single adapter covers both cases.

### 1.2 Managed S3-compatible storage

Prices exclude VAT. Prices were checked on 2026-10-08. When a figure comes only from a secondary source, it is marked **(unverified)**.

| Provider | Price | Egress | Notes |
|---|---|---|---|
| **Hetzner Object Storage** (FSN1/NBG1/HEL1, EU) | Base price billed hourly, capped monthly. It includes 1 TB of storage (744 TB-h) and about 1 TB of egress per month [8][9]. The base price is **€6.49/month** since 2026-04-01, up from €4.99 **(unverified: secondary sources [10][11]; Hetzner's page renders prices with JS)**. Extra storage is about €8.70 per TB-month **(unverified [11])**. | Ingress, internal eu-central traffic and API calls are free. Extra egress is about €1/TB **(unverified [11])**. | The minimum billable object size is 64 KB, so small thumbnails are billed as 64 KB [8][9]. Objects are immutable (write-once, read-many). Limits are 750 req/s per bucket and 50 M objects per bucket [9]. |
| **Scaleway Object Storage** (Paris) | Standard Multi-AZ about €0.0161/GB-month. One Zone about €0.0080/GB-month. Glacier about €0.0025/GB-month. [12] | 75 GB/month free, then €0.01/GB [12] | Billed per GB-hour, and requests are included [12] |
| **Cloudflare R2** | $0.015/GB-month. The free tier covers 10 GB-month, 1 M Class A and 10 M Class B operations. The pricing page was last updated 2026-10-01. [13] | Free [13] | Operations are billed after the free tier. It is a US company, which is a data-residency consideration. |
| **Backblaze B2** | From $6.95/TB-month. The first 10 GB are free. [14] | Free up to 3× average stored data, then $0.01/GB [14] | The pricing page does not confirm EU region availability [14] |

### 1.3 VPS baseline (Hetzner Cloud, DE/FI, excluding VAT and IPv4)

The second 2026 adjustment, effective 2026-06-15, applies to new orders and rescales [15]:

| Plan | Old | New (since 2026-06-15) |
|---|---|---|
| CX23 (2 vCPU / 4 GB / 40 GB, shared Intel) | €3.99 | **€5.49** |
| CX33 | €6.49 | **€8.49** |
| CAX11 (Arm) | €4.49 | **€5.99** |
| CAX21 (Arm) | €7.99 | **€10.49** |

The same page states that Object Storage, Volumes and storage products are **not affected** by the June adjustment [15]. The earlier 2026-04-01 increase applied to existing products too [16].

## 2. Cost estimate for Rome

### 2.1 Growth assumptions

These are assumptions to be validated, not measurements.

- Phone photo original: about 3–6 MB as JPEG and about 1.5–3 MB as HEIC (12 MP class). Use **5 MB** per image for budgeting.
- Derivatives per image: 3 or 4 WebP renditions (for example 320, 800 and 1600 px on the long edge, optionally 2560 px). That is about 20 KB + 100 KB + 300 KB (+ 700 KB), or **about 0.5–1.2 MB**.
- PDF: capped (see §4). Budget about 3 MB on average, plus a preview of about 150 KB.
- Each image therefore costs about **6 MB** with its original kept, or about **1 MB** if only derivatives and a sanitised master are kept.

| Scenario | Images | PDFs | Storage (originals kept) |
|---|---|---|---|
| Year 1, modest | 2,000 | 100 | ~12 GB |
| Year 3, active | 10,000 | 500 | ~62 GB |
| Year 5+, very active | 50,000 | 2,000 | ~306 GB |

Egress: most traffic is 800 px renditions of about 100 KB. Even 100,000 page views per month at about 1 MB each is about 100 GB/month. That is well within Hetzner's included 1 TB, and Hetzner Cloud servers include 20 TB of traffic [17]. No CDN is required at this scale.

### 2.2 Budget envelopes

| Setup | Monthly (excl. VAT) | Fits €20? |
|---|---|---|
| A. CX23 with local-disk storage (40 GB disk shared with Postgres) | €5.49 + IPv4 | Yes, but disk fills by around year 2–3. It then needs a Volume or an upgrade. Backups must leave the box. |
| B. CX23 + Hetzner Object Storage | €5.49 + €6.49 (unverified) ≈ **€12** + IPv4 | Yes. 1 TB covers every scenario above. With 22% Italian VAT it comes to about €14.6. |
| C. CX33 + Hetzner Object Storage | €8.49 + €6.49 ≈ **€15** + IPv4 | Yes, before VAT. About €18.2 with VAT, which leaves little room for backups. |
| D. CX23 + Scaleway One Zone / R2 / B2 (pay per GB) | €5.49 + under €1 at 12 GB, about €2.5–5 at 300 GB | Yes, and cheapest early on, but it adds a second vendor and cross-provider egress. |

Open point: whether the **€20 ceiling includes VAT** changes the margin for setup C and for off-site backups.

## 3. Pipeline outline (options, not a decision)

```
browser ──(1) request upload──▶ API: create pending Upload row, return presigned PUT (or accept multipart)
browser ──(2) PUT bytes──────▶ quarantine/ (private)
browser ──(3) "done"─────────▶ API: enqueue process_upload(id)
worker  ──(4) validate → extract metadata → sanitise → derivatives ─▶ private/ + derivatives/
worker  ──(5) mark Upload ready (or rejected with reason) ; UI polls / refreshes
moderation approves Submission ─▶ Documentation item becomes public (derivatives served)
Withdrawal ─▶ derivatives stop being served (no deletion)
```

### 3.1 Processing location: synchronous or worker

- FastAPI's `BackgroundTasks` runs in the same process after the response is sent. The docs recommend it for small jobs and point to a separate task queue for heavy computation across processes [18]. Decoding images and rendering PDFs is CPU- and memory-heavy, and it is an attack surface (malformed files). That argues for a **separate worker container** with its own memory and time limits, even if it shares the codebase.
- **Procrastinate** is a task queue that uses PostgreSQL (13+) as its backbone. It has async support, retries and periodic tasks, and it is MIT-licensed [19]. It needs no Redis or RabbitMQ, which keeps the Compose stack to app + worker + Postgres (+ optional S3). Celery requires a message broker such as RabbitMQ or Redis [18].
- A synchronous path is viable only for cheap checks: size, declared type and magic bytes. Derivatives should be asynchronous so the upload UX stays responsive and failures can be retried.

### 3.2 Image processing libraries

| Library | License | Notes |
|---|---|---|
| **Pillow** 12.3 | HPND (MIT-like) | Has a decompression-bomb guard: it warns above `MAX_IMAGE_PIXELS` and raises `DecompressionBombError` above 2× that [20]. `draft()` gives fast reduced JPEG decoding [20]. Reads and writes AVIF natively [21]. JPEG output contains EXIF **only if passed explicitly** [21]. |
| **pillow-heif** | BSD-3-Clause (bundled codecs have their own licenses) | Adds HEIC/HEIF decoding to Pillow [22], which matters for iPhone uploads. HEVC patent/licensing implications of the bundled codecs are not documented on the project page, so this needs checking. |
| **libvips / pyvips** | libvips LGPL-2.1+ [23]; pyvips MIT [24] | `thumbnail` combines load and resize with shrink-on-load, colour management and alpha handling [25]. It is low-memory and streams large images. `pyvips[binary]` wheels are self-contained but **lack PDF load** [24]. Metadata retention on save is controlled by `keep` (`ForeignKeep`) [23]. |

### 3.3 PDF first-page preview

| Library | License | Notes |
|---|---|---|
| **pypdfium2** (PDFium) | Apache-2.0 / BSD-3-Clause; PDFium BSD-style [26] | Wheels bundle PDFium. `page.render(...).to_pil()` produces a Pillow image [26]. Licence-friendly for a source-available, non-commercial project. |
| PyMuPDF (MuPDF) | **AGPLv3 or commercial** [27] | Capable, but AGPL linking is a licensing question for the LDR. Avoid unless the LDR accepts it. |

Render only page 1 at a capped DPI, in the worker, with a timeout. Serve original PDFs with `Content-Disposition: attachment` (or a sandboxed viewer) and a restrictive CSP. That keeps active PDF content from running in the archive's origin. This is a general security practice, not taken from a cited source.

### 3.4 EXIF/GPS handling

- Read metadata **before** sanitising: `DateTimeOriginal`, the GPS position, and the orientation.
  - Offer the date as a **suggested Observed date**, with precision and editable by the contributor.
  - Offer the GPS position as a **suggested Location** that the contributor must confirm. It is never stored automatically as the artwork's location, and never shown as the submitter's location.
- Apply the EXIF orientation to pixels, then **re-encode all public derivatives without EXIF, XMP or IPTC**. Keep only the ICC profile, or convert to sRGB. With Pillow, EXIF is omitted unless passed [21]. With libvips, use `keep` [23].
- The **original file** still contains GPS, the camera serial and similar data. The options are:
  - (a) keep it in a private prefix, never served publicly, for moderation and archival
  - (b) keep a sanitised lossless master and discard the raw original
  - (c) discard it after processing

  This is a privacy and retention decision for the spec.

### 3.5 Upload validation and limits

- Allowlist by **detected** type (magic bytes), not by extension or client MIME: JPEG, PNG, WebP, HEIC/HEIF, AVIF, PDF.
- Suggested starting limits, to be tuned:
  - images: 25 MB per file, 50 MP, so Pillow's bomb guard is tightened from its default
  - PDFs: 20 MB and a page cap (for example 200)
  - a per-Submission file count (for example 20)
  - a per-user daily quota
- Enforce the size limit at the reverse proxy, in the presigned URL's content-length condition and in the app.
- Fully decode in the worker. A file that fails to decode is rejected. Pending uploads that are never submitted are garbage-collected after N days.
  - Garage's lifecycle support covers `AbortIncompleteMultipartUpload` and `Expiration` [5].
  - Hetzner Object Storage is write-once [9]. "Moving" an object from quarantine means copy + delete.
- Malware scanning (for example ClamAV) is optional. Re-encoding images neutralises most payloads in images. PDFs are the residual risk.

### 3.6 Serving, moderation and Withdrawal

- Keep **all buckets/prefixes private**. Serve media through the app, with short-lived presigned GET URLs or an internal proxy route.
- This lets pending-Submission media and Withdrawn items be hidden by a database flag alone, with no object moves, which honours "Withdrawal is not deletion".
- A public bucket plus CDN would be cheaper on CPU, but makes Withdrawal depend on cache purges.
- Garage has no bucket policies, and Hetzner exposes public buckets by URL [5][9]. Both work with the private + presigned model.

## 4. Risks

1. **MinIO is no longer a viable default.** It is archived, distributed as source only and receives no CVE fixes [1]. Many tutorials still assume it.
2. **Price volatility.** Hetzner raised prices twice in 2026 [15][16]. The €20 ceiling has little slack once VAT, IPv4 and backups are included.
3. **A single VPS with local storage** has no durability without off-site backups. Media backups must be designed together with Postgres backups (see the "Operations" item on the map).
4. **Untrusted file parsing** (image and PDF decoders) is the main security surface. Isolate it in a worker with resource limits, and keep libraries patched.
5. **Licensing.** AGPL components (Garage, PyMuPDF), LGPL libvips, and HEVC codecs in HEIC support need an LDR note.
6. **Privacy.** Leaking GPS through originals or forgotten derivatives would expose contributors' movements.
7. **Hetzner's 64 KB minimum object billing and write-once semantics.** These are minor at this scale, but they shape the derivative and quarantine design [8][9].

## 5. Questions surfaced for other tickets

- Is the €20/month ceiling **including or excluding VAT**, and does it include off-site backups?
- **Retention of original files**: should the raw original (with metadata) be kept privately, sanitised, or discarded? What rights and privacy policy covers it?
- Should EXIF GPS and date be used as **suggestions** in the new-artwork journey? This is a UX and privacy question for the contribution flow.
- **Content rights at upload**: what licence or consent does the contributor grant for a photo, and is it recorded per Documentation item?
- **Backups of media** (bucket replication, restic to a Storage Box, and so on) belong in the Operations ticket.

## Sources

Accessed 2026-10-08 unless noted.

1. MinIO GitHub repository (archived 2026-04-25, README notice): https://github.com/minio/minio
2. Garage license (AGPLv3), per docs.rs crate page and project intro: https://docs.rs/crate/garage/2.4.1
3. Garage homepage (requirements): https://garagehq.deuxfleurs.fr/
4. Garage quick start (single node, image v2.4.1): https://garagehq.deuxfleurs.fr/documentation/quick-start/
5. Garage S3 compatibility reference: https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/
6. SeaweedFS README: https://github.com/seaweedfs/seaweedfs
7. RustFS README: https://github.com/rustfs/rustfs
8. Hetzner Object Storage product page: https://www.hetzner.com/storage/object-storage/
9. Hetzner Docs, Object Storage overview: https://docs.hetzner.com/storage/object-storage/overview/
10. Secondary: Hetzner pricing changes 2026 tracker: https://agentdeals.dev/hetzner-pricing-2026
11. Secondary: Sliplane, "5 Cheap Object Storage Providers in Europe in 2026" (July 2026): https://sliplane.io/blog/cheap-object-storage-providers-europe
12. Scaleway storage pricing: https://www.scaleway.com/en/pricing/storage/
13. Cloudflare R2 pricing (last updated 2026-10-01): https://developers.cloudflare.com/r2/pricing/
14. Backblaze B2 pricing: https://www.backblaze.com/cloud-storage/pricing
15. Hetzner Docs, Price Adjustment 15 June 2026 (last change 2026-07-08): https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
16. Hetzner press, statement on price adjustment as of 1 April 2026: https://www.hetzner.com/pressroom/statement-price-adjustment/
17. Secondary (20 TB traffic included with CX23): https://www.bitdoze.com/md/hetzner-cloud-review.md
18. FastAPI, Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
19. Procrastinate documentation: https://procrastinate.readthedocs.io/en/stable/
20. Pillow `Image` reference (12.3.0): https://pillow.readthedocs.io/en/stable/reference/Image.html
21. Pillow image file formats: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
22. pillow-heif: https://github.com/bigcat88/pillow_heif
23. libvips API (8.18): https://www.libvips.org/API/current/
24. pyvips README: https://github.com/libvips/pyvips
25. libvips resample (`vips_thumbnail`): https://www.libvips.org/API/current/libvips-resample.html
26. pypdfium2: https://github.com/pypdfium2-team/pypdfium2
27. PyMuPDF: https://github.com/pymupdf/PyMuPDF
