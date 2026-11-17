# Mithaq v0 — Product Specification and Complete Implementation Plan

**Revision:** 1.7 — host-only CI test strategy; legacy ZIP-overlay test-asset cleanup  
**Date:** 16 November 2026  
**Supersedes:** r1.6 for CI migration/cleanup details; earlier product decisions remain unchanged  
**Platform:** Native Android, Kotlin-first  
**Distribution target:** Google Play  
**Status:** Phase 0 implementation in progress; host-only CI and legacy overlay cleanup adopted

---

# Part I — Product specification

## 1. Executive product definition

Mithaq v0 is an offline-capable, local-first personal AI workspace for Android. It combines private on-device conversation, a persistent user-controlled knowledge library, semantic retrieval, guarded document handling, and a bounded agent mode in which application code—not the language model—authorizes operations.

The app is native Kotlin with Jetpack Compose. The main application does not have Internet permission. Model inference runs in a permission-isolated Android service if the descriptor-based runtime proof succeeds. A separately installed network companion, signed by the same publisher but running under a separate Android UID, owns the limited network capabilities needed for approved search, restricted page-text fetching, and staged model delivery.

The release is English-only. English is the UI and assistant default. Arabic is a planned future language and must be designed for at the architecture and data-model level, but it is not a supported v0 language. French is excluded from the product scope.

### 1.1 Product principles

1. **Local-first:** conversation, files, embeddings, retrieval, memory and model inference remain on the device. Network access is limited to user-approved search/fetch and user-requested model delivery through the companion.
2. **Evidence and provenance:** every imported, retrieved or externally obtained item retains source metadata and traceable lineage.
3. **Untrusted-by-default:** content never becomes trusted because it is local, user-selected, highly ranked, classifier-clean or from a reputable domain.
4. **Application-enforced authority:** model output is a proposal. A deterministic Capability Broker authorizes every tool and state change.
5. **Explicit human authority:** consequential changes and every fetch require a fresh, app-generated confirmation. The model cannot approve its own actions.
6. **Fail closed at trust boundaries:** if a required guard, model-integrity check, source grant or authorization service is unavailable, the affected capability is disabled rather than silently weakened.
7. **Useful offline degradation:** local chat and other already-qualified local features continue to work when the companion or network is unavailable.
8. **No hidden capability:** users can see, cancel and revoke active model, source, search and fetch operations.

## 2. Agreed v0 decisions

The following table is the binding interpretation of the ten owner choices, reconciled with the latest language correction.

| # | Decision area | Owner choice | Normative v0 outcome |
|---:|---|:---:|---|
| 1 | Language and dialect profile | A, then clarified | **English only for v0; English is the default.** Arabic is a future language, with an MSA-first/dialect-aware profile to be qualified later. **No French.** |
| 2 | RAG persistence | A | Persistent, user-managed local Knowledge Library. Persistent sources, chunks, embeddings and lexical index are retained encrypted. Task-only attachments remain ephemeral unless explicitly saved. |
| 3 | Document formats | A | TXT, Markdown, JSON, CSV and **text-based PDF**. PDF ships only after parser and hidden-text security gates pass. Scanned PDF OCR, Office, archives and executable/container formats are out of v0. |
| 4 | Multimodal scope | C | **Image input only** through Android Photo Picker or document picker. No audio, speech, video, camera capture or image-based RAG in v0. Exact Gemma 4 E4B image path must pass a model/runtime/device gate. |
| 5 | URL fetching | B | Search plus a restricted, one-URL-at-a-time page-text fetch. Every fetch requires separate user approval and strict SSRF controls. If fetch qualification fails, ship search-only. |
| 6 | Classifier architecture | B | ONNX Runtime Android CPU is the selected deployment direction. PromptGuard 2 86M is the first primary candidate; a second classifier is shadow-evaluated off the critical path. No dual-model production requirement. |
| 7 | Inference isolation packaging | B | Prove the custom read-only file-descriptor JNI bridge into `android:isolatedProcess` first. Main app and network companion are separate packages. If inference FD isolation cannot be made reliable, evaluate a separate inference companion APK; never silently fall back to a privileged ordinary process while claiming equivalent isolation. |
| 8 | Device baseline | B | Android 15 / API 35+, `arm64-v8a`; **8 GB RAM is the minimum qualification target**, **12 GB recommended**. 8 GB devices are not generally supported until tested. |
| 9 | Model delivery | B | Staged, user-initiated model installation. Gemma during setup; embedding model when Knowledge is first activated; classifier before document/RAG or external-content ingestion is enabled. SAF import is the recovery path. |
| 10 | Distribution | A | Google Play. Publish the main app and the Network Companion as separately listed apps. The main app opens the companion's Play listing when needed; it does not silently install another APK. |

## 3. Launch language policy

### 3.1 v0 language contract

- The only declared v0 product language is English.
- English is the initial UI language, default assistant response language, system instruction language and supported retrieval evaluation language.
- The app must not expose French as a locale or claim French support.
- Arabic is not a supported v0 language even though a base model or an embedding model may process some Arabic text. Unsupported language behavior must not be represented as qualified product support.
- The language preference model and resource structure must allow adding Arabic without a database migration or redesign of prompts, UI navigation or document metadata.

### 3.2 Future Arabic preparation

Future Arabic qualification is planned, not delivered in v0. It must include:

- Modern Standard Arabic as the default written response profile, with dialect understanding tested across at least Egyptian, Levantine, Gulf and Maghrebi varieties.
- Arabic without diacritics, with diacritics, spelling variants, Arabic-English code-switching and Arabizi in the evaluation corpus.
- RTL screen layout, mixed-direction identifiers and robust Unicode/bidi rendering.
- Arabic semantic retrieval, same-language and cross-language queries, Arabic tokenizer behavior and source citation correctness.
- Prompt-injection classifier evaluation specifically in Arabic; current PromptGuard 2 published test languages do not establish Arabic performance.
- Arabic benign-twin testing to avoid blocking ordinary imperatives, quotations, educational material or religious/legal discussions.

The app should use locale-aware string resources, logical start/end layout properties, locale-independent identifiers and an explicit `LanguageProfile` abstraction. It must not implement a partial or unqualified Arabic UI in v0.

## 4. User modes and principal workflows

### 4.1 Chat Mode

Chat Mode is local and offline by default.

- Streams answers from local Gemma 4 E4B.
- Stores conversations in the encrypted local database.
- Supports text and optional image attachments once the image-input gate passes.
- Can use current-turn attachments and Knowledge Library sources only when their source grant and content-guard state permit them.
- Does not expose model-invoked tools, search, page fetch, memory writes or document writes.
- Displays source citations when RAG material is used.
- Renders Markdown and code through a safe allowlist. Raw HTML, JavaScript, remote images, automatic link previews and executable content are disabled.

### 4.2 Agent Mode

Agent Mode must be deliberately enabled by the user for a bounded session.

- The model may propose calls only to application-registered tools.
- All tool proposals are parsed into strict typed DTOs and passed to the Capability Broker.
- T0 pure computation can run automatically.
- T1 reads may run automatically only when covered by a current, narrow, user-granted scope.
- T2 local state changes require fresh, app-generated confirmation tied to an exact action payload and an expiry.
- T3 network actions require their own consent rules. Search may use a narrowly bounded session grant after exact-query approval; every page fetch requires separate per-URL approval.
- Denial, timeout, revocation or stale approval cannot be bypassed by model retries.
- Tool count, cycle count, content bytes, time, context tokens and output size are bounded.

Search approval never authorizes fetching a result URL. A search session grant is not a fetch grant.

### 4.3 User-facing screens

1. **Chat:** conversation list, streaming response, text/image attachment controls, source citations and mode indicator.
2. **Knowledge:** persistent sources, collections, source status, indexing progress, retrieval preview, re-index/remove/revoke controls.
3. **Memory:** proposed, approved, edited and deleted memories with source lineage; memory remains distinct from the Knowledge Library.
4. **Agent activity:** current operation, requested capability, scope, approval state, search/fetch progress and cancellation.
5. **Models:** Gemma, embedding and guard artifact status; staged download/import; hash, license and compatibility state.
6. **Security:** vault state, grants, guard state, companion connection, audit events, source exposure and revoke controls.
7. **Settings:** English language default, privacy, lock timeout, network provider, resource limits and device diagnostics.

Visual polish is subordinate to complete authorization, guard, lifecycle and error handling. Security state must never be represented only through color or model-generated prose.

## 5. Model and inference specification

### 5.1 Generative model

- Primary model: Gemma 4 E4B instruction-tuned, official LiteRT-LM `.litertlm` artifact.
- No remote inference endpoint.
- Runtime direction: LiteRT-LM Android, CPU and GPU backends qualified separately.
- Model file, size, SHA-256, immutable upstream revision, runtime version, ABI/backend and license must be pinned in a manifest embedded in the signed app release.
- No dynamic `latest.release` dependency in a production build.
- Model version changes require a new compatibility and performance record.

The official benchmark currently lists the E4B artifact at approximately 3,654 MB. The published Android benchmark is for a Samsung S26 Ultra and reports materially different CPU/GPU latency and memory numbers; it is not proof that an 8 GB device will run the model successfully. [R1]

### 5.2 Isolated inference boundary

Target architecture:

The main app orchestrates three distinct no-permission isolated Android workers: **Generation Worker**, **Embedding Worker** and **Guard Worker**. Each worker runs under `android:isolatedProcess="true"`, has no network or app-private storage access by path, and receives only the bounded request payloads and model/cache descriptors it requires. The workers are not allowed to call one another or access the database. The main app remains the policy, storage and orchestration authority. The FD/byte-buffer loading path for each runtime is an explicit feasibility test; isolation is not claimed for a worker whose runtime requires privileged path access.

1. The main app verifies model hash and size, then opens the model using a read-only file descriptor.
2. It passes a narrowly scoped `ParcelFileDescriptor` to the isolated inference service using Binder.
3. The service is declared with `android:isolatedProcess="true"`, has no permissions of its own, and receives only request data and the descriptors required for inference.
4. A small reviewed JNI bridge duplicates the descriptors with close-on-exec semantics and passes them to the LiteRT-LM native C API.
5. Model scratch/cache files use an equally narrow writable descriptor where required. The worker cannot open arbitrary app-private paths.
6. The worker receives text and, for image turns, bounded image bytes; it does not receive arbitrary filesystem paths or network handles.
7. The service streams typed token events back, supports cancellation, and closes native resources on lock, session end, memory pressure or process death.

**No ordinary-process fallback is permitted under the same isolation claim.** If the native descriptor path fails, the choices are to revise the isolation architecture, move inference into a separately packaged no-network companion, or change the model/runtime. The failure must be documented as an architecture decision, not hidden.

Android documents that an isolated service runs in a special process with no permissions of its own. [R2] The LiteRT-LM Kotlin Android guide currently shows a path-based `EngineConfig(modelPath=...)`. A public LiteRT-LM issue describes the missing LLM Kotlin descriptor input, a native raw-FD API and a community prototype that reportedly worked on Android 16 using LiteRT-LM v0.16.1. This is useful feasibility evidence, but it is not upstream Kotlin API support and is not Mithaq's proof. [R3, R4]

### 5.3 Runtime versioning

LiteRT-LM v0.19.1 was released on 5 November 2026 and includes a breaking C API 1.0.0 change. It is the first candidate for the spike, not a blindly accepted final pin. The C headers, native libraries, Kotlin artifact and JNI bridge must be built and tested as one version-locked unit. [R4]

### 5.4 Embedding model

- Primary candidate: EmbeddingGemma 2 text-only 270M LiteRT-LM artifact.
- Do not load the optional vision/audio encoders for document text RAG.
- Initial vector dimension: 512, normalized; compare 256 dimensions in retrieval tests.
- Store Float32 vectors initially. Compression or quantization requires retrieval-parity evidence.
- Pin the exact model and tokenizer/template revision.
- Apply the official task prefixes consistently. For search queries and documents, use the exact current model-card templates; a template change invalidates the compatible vector space and requires re-indexing.
- Serialize embedding and generation workloads through a resource scheduler. Avoid concurrent model loads on constrained devices.

The EmbeddingGemma 2 model card describes a 270M text backbone, selectable encoders, 100+ language coverage and Matryoshka dimensions. These are model-level capabilities, not a guarantee of Mithaq retrieval quality in every language. Its future Arabic use must be benchmarked separately. [R5]

### 5.5 Resource scheduling

The application maintains a single model-resource coordinator. It schedules:

- Gemma generation;
- EmbeddingGemma indexing/query embedding;
- Prompt-injection classifier inference;
- optional vision path for image turns.

On 8 GB candidate devices, avoid simultaneous large inference workloads. The coordinator may close/reload an engine, reject a concurrent request with a clear state, or queue work. It must not silently lower context length, switch model or change backend without reporting the compatibility profile.

## 6. Image-only multimodal input

v0 supports a user-selected image attachment only.

- Use Android Photo Picker or SAF document picker; no broad storage permission.
- No camera permission, microphone permission, audio recording, speech recognition, audio generation or video input.
- No image embeddings, image indexing or image-based RAG.
- An image may be attached to a single conversation turn and is not persisted in the Knowledge Library unless a separate explicit file-save workflow is introduced.
- Strip EXIF metadata from the model-facing image; bound encoded bytes and pixel dimensions; decode safely; downsample before passing to inference; reject malformed, unsupported or oversized images.
- Transfer the bounded image payload to the isolated worker as bytes, not as an arbitrary path.
- Exact Gemma 4 E4B image-input support on the chosen LiteRT-LM Android version and supported device matrix is a release gate. If it fails, v0 ships text-only rather than substituting another unqualified model.

The LiteRT-LM Android guide exposes image and audio content variants for supported multimodal models, and v0.19.1 release notes describe Gemma 4 vision/audio support on the Artisan GPU backend. This confirms the direction exists in the runtime ecosystem; the exact E4B Android path still requires a Mithaq device test. [R6, R4]

## 7. Persistent Knowledge Library and semantic RAG

### 7.1 Persistence model

- Knowledge Library is persistent and managed by the user.
- Sources are grouped into user-created collections or default collections.
- Source originals, extracted text, chunks, vector records and FTS entries remain local and encrypted.
- Current-turn attachments are ephemeral by default and are not automatically copied into the persistent library.
- A user action is required to save an attachment permanently.
- Approved memory is a separate entity and workflow, not a synonym for source documents or retrieved chunks.
- Revocation immediately excludes a source from new retrieval; deletion removes its index, vectors, extracted data, stored original and downstream memory lineage as specified in the delete workflow.

### 7.2 Accepted formats

v0 format allowlist:

- `.txt`
- `.md` / `.markdown`
- `.json`
- `.csv`
- text-based `.pdf`

PDF support is included in the intended format scope but gated. The parser must pass malformed-document, hidden/invisible-text, object-count, page-count, decompression, time and memory limits. The UI must report partial extraction and must never label it fully indexed. Scanned PDF OCR is not part of v0. Office formats, e-books, archives, executables and arbitrary containers are excluded.

### 7.3 Ingestion pipeline

```text
SAF selection and scoped read grant
  -> identity, MIME, extension, byte-size and signature checks
  -> bounded parser and extraction
  -> Unicode/text normalization and structural cleanup
  -> deterministic input checks
  -> primary content classifier (once qualified)
  -> quarantine or accept for indexing
  -> structure-aware chunking
  -> document embedding
  -> encrypted vector persistence + FTS5 lexical index + provenance
  -> indexed source state and retrievable-source grant
```

No document code is executed. Parsers do not load remote resources. Imports are cancellable and resumable from durable checkpoints. Parser failures and quarantined blocks are visible.

### 7.4 Chunk and vector defaults

Initial values to measure, not immutable guarantees:

- Structure-aware chunks targeting 350–500 embedding tokens.
- 50–80 token overlap only where needed for continuity.
- Preserve headings, paragraph boundaries, list structure, code fences and CSV row boundaries.
- Store source ID, source revision, collection ID, title, heading path, chunk ordinal, content hash, source offsets, parser completeness, classifier model/version/verdict and grant ID.
- 512-dimensional normalized Float32 vectors as the initial configuration; benchmark 256 dimensions before freezing.
- Cache key includes content hash, extraction version, chunker version, embedding model/revision, task-prefix version and vector dimension.

### 7.5 Hybrid retrieval

RAG is semantic-first but hybrid. For each query:

1. Verify the current task's source grants and selected collections.
2. Embed the query using the model's search-query instruction prefix.
3. Run dense vector retrieval over only eligible sources.
4. Run FTS5 lexical retrieval over the same eligible sources.
5. Merge ranked lists using Reciprocal Rank Fusion (or a measured alternative).
6. Apply source-active, freshness, revision, privacy and provenance filters before final context assembly.
7. Deduplicate near-identical overlapping chunks.
8. Cap the candidate set and selected context (initial proposal: top 20 candidates, up to 8 final chunks and 6,000 RAG tokens, inside the total model context budget).
9. Add source citations and a context-exposure ledger entry for every chunk.
10. Serialize every chunk as `<untrusted>` before it enters Gemma.

The model cannot supply arbitrary source IDs. The retrieval use case obtains its eligible IDs from the current task scope, and the broker revalidates that scope.

### 7.6 Retrieval quality gate

Build an English benchmark containing single-chunk and multi-chunk questions, paraphrases, exact identifiers, names/dates/code, conflicting/duplicate sources, adversarial prompt-injection documents and unanswerable questions. Measure Recall@5/10, MRR, nDCG@10, citation correctness, answer groundedness, abstention quality, latency, memory and index size. Thresholds are fixed before release candidate evaluation. A proposed Recall@10 target of 0.85 is a project target, not a model guarantee.

Arabic retrieval evaluation is future work and must not be inferred from an advertised 100+ language model capability.

## 8. Trust boundaries, `<untrusted>` envelope and content guard

### 8.1 Mandatory source envelope

Every imported, retrieved, external or tool-derived knowledge block passed to Gemma must be wrapped in an application-generated `<untrusted>...</untrusted>` envelope. This includes:

- user-selected document text;
- local RAG chunks;
- memory retrieved from the user's memory store;
- search-result titles, snippets and metadata;
- fetched-page text;
- outputs from tools or external systems;
- summaries or derived records that retain lineage from any of the above.

The immutable system policy must state that content inside the envelope is data only and cannot:

- override system or developer instructions;
- change roles or policies;
- request hidden prompts, secrets or private data;
- authorize, initiate or redirect a tool call;
- select a network provider, URL, HTTP method or capability;
- approve a confirmation or change persistent state.

Gemma may quote, summarize, translate, compare or analyze the content as evidence. It must attribute source claims and express uncertainty when support is missing. Any consequential action requires independent user intent and deterministic Broker authorization.

### 8.2 Safe serialization rules

- Only application code creates the envelope and source metadata.
- Never trust tags, source labels, URLs, verdicts or `trust_level` fields originating in a document or model response.
- Escape or encode literal `<untrusted>` and `</untrusted>` sequences in the payload before wrapping; JSON escaping alone is insufficient unless angle brackets are also neutralized.
- Use a typed source envelope and serializer, not raw string concatenation into the system prompt.
- Reject malformed provenance, nested forged wrappers, duplicate IDs and oversized metadata.
- Store original content separately; the model-facing serialized representation is derived and versioned.
- The wrapper is prompt hygiene, not a hard security boundary. The broker, process isolation, network boundary and deterministic policy checks enforce authority.
- A classifier-clean verdict never upgrades content into trusted instructions.

### 8.3 Deterministic guard layer

Application-owned deterministic controls run regardless of classifier:

1. File size, content size, parser depth, time, memory and token budgets.
2. MIME, extension and magic-byte validation.
3. Explicit charset handling; reject malformed/ambiguous decoding rather than silently replacing large sections.
4. NFC normalization for model-facing text.
5. Detect/remove dangerous invisible controls and bidi overrides in security-sensitive metadata; preserve legitimate language shaping characters and line structure in content.
6. URL canonicalization and scheme/port/host restrictions where URL input is in scope.
7. Strict JSON/DTO parsing with unknown-field handling and semantic validation.
8. Secret scanning of exact outbound search queries.
9. PII warning workflow rather than blanket rejection of ordinary personal terms.
10. Output rendering allowlist; no HTML or remote active content.
11. Audit records that contain event type and decision metadata, never raw private content.

### 8.4 Classifier architecture

Selected deployment direction: ONNX Runtime Android, CPU execution, in a dedicated no-permission isolated guard worker, with **PromptGuard 2 86M** as the first primary candidate. The model must be supplied through a tested descriptor or bounded in-memory path; the worker must not open app-private model paths or have network access. The second classifier is used for offline/shadow comparative evaluation and is not a required simultaneous production runtime.

The PromptGuard 2 model card describes binary benign/malicious classification for explicit instruction supersession and a 512-token context. It also states that its published evaluation languages include English, French, German, Hindi, Italian, Portuguese, Spanish and Thai. Arabic is not in that evaluated list. v0 claims English only. [R7]

Required classifier qualification:

- Obtain a fixed model revision, tokenizer and license materials.
- Reproduce a reference Transformers implementation on a versioned test set.
- Produce a reproducible ONNX conversion and inspect operator compatibility.
- Run through the official ONNX Runtime Android package on CPU.
- Prove exact tokenizer parity, including the model's adversarial tokenization behavior. A generic tokenizer substitution is prohibited.
- Compare Android class scores/logits with the reference runtime and define numeric tolerances.
- Scan all content using bounded overlapping windows. The working proposal is 384 tokens with 64-token overlap, but this must fit the actual tokenizer and full 512-token context; no unscanned tail may be treated as clean.
- Establish calibrated thresholds and per-class false-positive/recall targets on matched attack/benign pairs.
- Measure latency, peak RSS, thermal impact and battery use on every reference device.
- Have legal review approve the applicable Llama 4 Community License and redistribution/attribution obligations before bundling the weights. [R8]

PromptGuard is one layer, not a proof of safety. It focuses on explicit known attacks; it may miss adaptive or indirect cases. Search results, page text and documents remain untrusted even when the classifier returns benign.

### 8.5 Failure policy

- **Plain text local chat:** remains usable if the classifier is unavailable.
- **Document ingestion/RAG:** may store a source for the user, but indexing and model-context injection remain disabled until the primary classifier and serializer are qualified and operational.
- **Search/fetched content:** never passed to Gemma unless the primary classifier is qualified, healthy and has scanned every segment.
- **Classifier timeout, crash, model mismatch or unsupported language:** quarantine or block the affected content from model context; never silently switch to deterministic-only while claiming guarded ingestion.
- **Shadow classifier:** can report benchmark results but cannot independently enable a capability.

### 8.6 Secrets and PII

- A high-confidence API key, bearer token, JWT, private key or cloud credential match in an outbound search query causes a hard block.
- Ordinary PII produces a warning and exact-query confirmation, not a universal rejection.
- Never log the matched value. Audit only category, decision and a non-reversible event identifier.
- Search query disclosure is displayed before network transmission. Selected local document contents and the full conversation are never silently attached to a search query.

## 9. Search and restricted page-text fetch

### 9.1 Search

- Network provider is Off by default.
- Primary v0 path: Parallel Search MCP / approved Search endpoint, with only the `web_search` capability allowed. The keyless offering has rate limits; only explicitly permitted calls are made. [R9]
- The provider's `web_fetch` capability is not exposed or invoked. Mithaq owns its restricted fetch path.
- Tavily is not a keyless alternative: its API uses API-key authentication. It may be added only as an optional user-configured provider with its credential encrypted and managed by the companion. [R10]
- Provider hostname, endpoint, method and parameters are fixed in code. The model cannot supply or modify them.
- User sees the exact query, provider and destination before it leaves the device.
- Exact-query approval is required initially. A bounded provider-scoped search grant may be offered after the user understands its scope; no grant covers fetch.
- Search response schema, result count, bytes, call count, rate and timeout are bounded.
- Every result is normalized, scanned by the primary classifier, wrapped as untrusted and shown with source provenance.
- Result URLs are references only. They are not automatically opened, fetched or previewed.

### 9.2 Restricted `fetch_page_text`

The fetch capability accepts only:

1. a URL reference from a search result currently shown in the UI; or
2. a URL explicitly entered or selected by the user.

The model may request a fetch for an existing URL reference, but it cannot construct, modify or substitute the URL. The app displays the exact canonical URL, hostname and disclosure. Every fetch needs fresh app-generated confirmation. Search approval does not authorize fetch.

Allowed behavior:

- HTTPS, port 443, GET only.
- Reject URL userinfo and IP-literal hosts; no credentials, cookies, browser session, authorization header, client certificates or user-agent impersonation.
- No POST/PUT/PATCH/DELETE.
- No WebView, headless browser, JavaScript, service worker, CSS, iframe, image, font or subresource loading.
- Accept only `text/html`, `application/xhtml+xml` and `text/plain`.
- No PDF, Office, archives, executables, images, audio/video or binary downloads in the fetch path.
- Do not persist raw page content by default. Saving as a knowledge source is a distinct user action with original URL and retrieval time preserved.
- Fetched content is always untrusted and never automatically becomes durable memory.

### 9.3 SSRF and connection-boundary controls

- Strict URI parsing; IDNA/STD3 hostname validation; reject malformed escapes, ambiguous host encodings, bidi controls, userinfo, unsupported schemes/ports and unnecessary fragments.
- Resolve A and AAAA records before connecting. Reject a hostname if any returned address is loopback, private, link-local, multicast, reserved, unspecified, documentation-only or otherwise non-public.
- Pin the validated address for the actual socket connection to prevent DNS time-of-check/time-of-use rebinding; retain TLS certificate/hostname verification against the canonical hostname.
- Revalidate every redirect; allow at most two same-origin redirects. Reject scheme, host or port changes and unsupported downgrade paths.
- Reject mixed public/private DNS answer sets rather than choosing only the public address.
- Bound connection/read timeouts, response headers, compressed and decompressed body sizes, parser depth/node count and extracted text length. Reject compression bombs and malformed encodings.
- Network client must not silently follow redirects before policy code inspects them.
- If the implementation cannot guarantee pinning and redirect controls at the actual connection boundary, fetch is disabled. Search-only remains a complete supported fallback.

Initial budget proposals: 10 search results/query; 128 KiB normalized search response; 256 Unicode scalars/1,024 UTF-8 bytes per query; 2 MiB compressed and decompressed fetch body; 40,000 extracted Unicode scalars plus token cap; one in-flight fetch per session; two redirects maximum. These values must be fuzz-tested and frozen before release.

## 10. Capability Broker and action authority

The model never receives credentials, permission grants or direct handles to privileged APIs.

### 10.1 Tool classes

- **T0:** pure deterministic computations (for example calculator or text formatting); automatic within explicit request scope.
- **T1:** read-only access to a selected local file, current conversation or already-authorized source; automatic only within a current scoped grant.
- **T2:** local state changes such as writing a file, editing/deleting memory, changing persistent settings or deleting sources; fresh explicit confirmation.
- **T3:** network operations such as search and page fetch; separate user-approved consent rules. Every fetch requires a new confirmation.

### 10.2 Broker invariants

- Registry is application-owned and immutable for the installed version.
- Model tool proposals are untrusted input.
- Strict DTO/schema validation and semantic validation run before authorization.
- Each proposal is checked against the current user request, current task, source grants, capability scope, quotas, expiry and target object.
- Confirmations are app-generated and bind to a canonical hash of the exact proposed operation and target. Any field change invalidates approval.
- Model-provided `approved=true`, tool names, source IDs, session IDs, URLs or claims about consent have no authority.
- Denied actions are not retried until the user changes the request or grant.
- Side effects are idempotent where possible and produce a content-free audit event.

## 11. Network companion and package distribution

### 11.1 Package architecture

- Main app: no `INTERNET` or `ACCESS_NETWORK_STATE` permission; local database, model orchestration, UI, user grants, broker and encrypted files.
- Network Companion: separate package and Android UID, signed by same publisher; contains only approved network clients, fixed host allowlists, limited model transfer and typed Binder service.
- Companion service is signature-protected and verifies caller UID/package/signature and protocol version.
- No shared UID; no generic URL fetch, generic HTTP proxy or caller-supplied download URL.
- Main app sends typed request DTOs containing only the approved exact query, URL reference or artifact ID after consent. It does not send conversation history or private documents by default.
- Companion cannot read the main app's sandbox, database, vault or model directory.
- Companion connection failure or incompatible version disables only network operations.

### 11.2 Companion installation on Google Play

The two APKs are separately published and independently updated. When a user enables a network feature without the companion, Mithaq opens the companion's Google Play listing and explains why it is required. The app does not silently side-load or programmatically install the companion.

### 11.3 Model transfer

- Signed main-app manifest and companion-side allowlist both contain the immutable model artifact ID, fixed source URL(s), exact size, SHA-256 and allowed host/redirect policy.
- Main app requests a known artifact ID, never a URL.
- Companion streams bytes through a bounded pipe/descriptor to the main app; it never writes to main-app storage.
- Main app writes to an app-private `.part` file, checks exact byte count and SHA-256 itself, then atomically promotes the artifact.
- Cancelled, interrupted, truncated, oversized or mismatched downloads are not installable and are removed or safely resumed according to a tested protocol.
- User receives a storage estimate and Wi-Fi/mobile-data choice before transfer.
- SAF model import is a user-initiated fallback with identical manifest/hash validation.
- No remote model catalogue or mutable remote manifest is accepted.

The E4B model is roughly 3.65 GB. Google Play's beta on-device AI packs are currently limited to 1.5 GB per AI pack and 4 GB cumulative generated app size, so they are not the default delivery path for this artifact. [R1, R11]

## 12. Persistence, vault and privacy

Use Room with SQLCipher for structured data, Android Keystore for key protection and a separate per-file encryption key for persistent source originals and attachments. Cryptographic implementation must rely on reviewed platform/library primitives; no custom cryptography.

### 12.1 Core entities

- `Conversation`, `Message`, `MessageAttachmentRef`
- `KnowledgeCollection`, `KnowledgeSource`, `SourceGrant`, `SourceRevision`, `ExtractionRecord`
- `DocumentChunk`, `ChunkEmbedding`, `FtsDocument`
- `MemoryRecord`, `MemorySourceLineage`
- `CapabilityGrant`, `AgentSession`, `SearchSessionGrant`
- `ToolExecution`, `ConfirmationRequest`, `AuditEvent`
- `ModelArtifact`, `ModelManifestRecord`, `ModelInstallState`
- `ContextExposure`, `ContextExposureSource`
- `FetchRecord` (metadata only unless separately saved)

### 12.2 Data rules

- Vault states: Locked, Unlocking, Unlocked, Locking.
- Database is closed or key-unavailable when locked.
- Lock cancels inference, indexing, search and fetch; closes workers and releases references.
- No automatic cloud/device-to-device backup. Exclude vault data and sensitive model artifacts from backup unless the user later opts into a separately designed encrypted export.
- Production logs must not contain prompts, documents, queries, fetched body text, secrets or embeddings.
- Persist only source metadata and content necessary for the user-selected function.
- Delete/revoke workflows include source data, derived chunks, embeddings, FTS rows, cached content, grants and dependent memory lineage.
- Conversation export is out of v0 unless separately scoped and reviewed.

## 13. Device and support policy

Candidate floor: Android 15 / API 35+, arm64-v8a, 8 GB RAM minimum qualification target, 12 GB recommended. This is a target profile, not a blanket compatibility guarantee.

Release support requires at least three physical reference devices covering a lower-memory device, a mainstream device and a flagship. Each must be tested on supported OS versions for:

- cold/warm model load and time-to-first-token;
- decode speed and output stability;
- peak RSS, total app PSS and memory pressure;
- GPU and CPU fallback;
- repeated generation, cancellation and worker restart;
- embedding indexing and retrieval;
- classifier latency and accuracy;
- image input if enabled;
- thermal throttling, battery and background lifecycle;
- low-storage and interrupted download behavior.

If 8 GB devices fail, do not claim the baseline works. The owner must choose a higher RAM floor or explicitly approve a smaller model variant after quality testing. No automatic model swap that hides the downgrade.

## 14. v0 exclusions

- French language support.
- Arabic UI, Arabic guard qualification or Arabic RAG claims (planned future release).
- Audio, speech, video, live camera or screen capture.
- Image-based RAG, OCR for scanned PDFs and Office/archive parsing.
- General-purpose browser, WebView, arbitrary downloads or provider-controlled page fetch.
- Unbounded autonomous agents, background agents or scheduled autonomous actions.
- Arbitrary shell, Python, JavaScript execution or code interpretation.
- Cloud inference or user-content upload beyond explicitly approved search query and fetch request.
- Model-created permissions, persistent grants or confirmations.
- Automatic network fallback to another provider.

## 15. Product acceptance criteria

v0 is functionally complete only when:

1. English-only Chat Mode runs locally and survives network unavailability.
2. Gemma inference uses the verified isolated boundary; no privileged path fallback is present.
3. Main package has no Internet permission; the companion is a separately signed/UID-isolated package.
4. Encrypted vault and persistent Knowledge Library support create, index, retrieve, revoke and delete.
5. All retrieved/imported/external/tool-derived context is app-wrapped as untrusted and included in the exposure ledger.
6. Text and PDF parsers pass bounds, fuzz and hidden-text qualification; otherwise PDF is clearly disabled and the supported-format declaration is narrowed before release.
7. Semantic + lexical retrieval passes predeclared English quality thresholds and source attribution tests.
8. Primary classifier has reproducible Android parity, acceptable device cost, legal approval and matched-pair evaluation; otherwise document/RAG and external context injection remain disabled.
9. No untrusted content is treated as authority based on classifier output or source reputation.
10. Capability Broker rejects forged tools, IDs, scopes, stale approvals and changed action payloads.
11. Search query approval and privacy screening work; no query or private document is silently transmitted.
12. Fetch is either fully qualified against the SSRF checklist or disabled; search-only remains available.
13. Image attachments pass the exact model/runtime/device gate or are excluded from the release build.
14. Downloads verify the exact size/hash before model activation; failed transfers cannot be loaded.
15. No open critical/high security defects remain; SBOM, notices, model licenses, test reports and device matrix are included in the release evidence.

---

# Part II — Complete implementation plan

## 16. Implementation strategy and gating

The implementation starts now with Phase 0. This means the project is ready for engineering work, not that every feature is already feasible without qualification. The plan deliberately proves the most expensive unknowns before the feature surface grows.

Three major gates control the first full implementation:

- **G1 — Isolated local inference:** descriptor-based Gemma 4 E4B loading, cache handling, streaming, cancellation and restart inside the isolated service.
- **G2 — Content-guard deployment:** reproducible PromptGuard 2 86M ONNX + tokenizer + CPU parity and legal path.
- **G3 — Restricted fetch:** connection-level SSRF controls, DNS pinning, redirects and bounded extraction.

Two additional gates affect scope:

- **G4 — Hardware floor:** prove E4B and required engines coexist on the 8 GB qualification device; otherwise raise the floor or obtain approval for an alternative model.
- **G5 — Image input:** demonstrate Gemma E4B image input on the selected runtime and physical devices.

Failure handling is explicit:

| Failed proof | Safe outcome |
|---|---|
| G1 inference FD isolation | Do not ship a privileged ordinary-process workaround. Revisit the worker architecture or test the separate inference companion APK. |
| G2 classifier | Keep plain local chat; disable model-context ingestion of user documents, RAG and external search/fetch content until another classifier is qualified. |
| G3 SSRF/fetch | Disable page fetch; retain search-only. |
| G4 8 GB memory/thermal floor | Raise the supported RAM floor or seek owner approval for a smaller model; do not claim untested support. |
| G5 image input | Ship text-only v0; no substitute model without a new decision. |

## 17. Phase 0 — Architecture freeze and technical feasibility proofs

**Goal:** Establish that the chosen boundaries can be built on real Android devices before committing to the full implementation.

### Work items

1. Create the Git repository skeleton, Gradle version catalog, dependency verification and CI workflow for both packages.
2. Create a minimal main Compose app and a separately signed Kotlin Network Companion sample.
3. Implement a small signature-protected Binder service. Cover its AIDL/service method contract, manifest permission declaration, package visibility and protocol compatibility with host-JVM integration tests.
4. Use JVM unit/host integration tests for companion-absent, outdated-protocol, wrong-caller-policy and service-restart state-machine behavior through fakes; do not run Android E2E or instrumentation tests on an emulator in CI.
5. Build the isolated inference service with no permissions and a typed Binder interface. Runtime UID, Binder-kernel authorization and private-file isolation are separate device qualification gates; host tests must not claim to prove them.
6. Verify SHA-256 and open Gemma read-only FD in the main app; pass model FD and required cache FD through Binder.
7. Build the minimum JNI bridge against the exact LiteRT-LM version candidate; test C API 1.0.0 signatures and native ABI compatibility.
8. Demonstrate load, stream, cancellation, lock, service death, repeated restart and cache recovery on Android 15 and current Android.
9. Specify and review the isolated worker's inability to read app-private files by path, use sockets or access unrelated provider/service handles. These are Android runtime properties and remain unverified by JVM/host tests; require separate device evidence before production claims.
10. Test EmbeddingGemma 2 text-only artifact and Kotlin `EmbeddingEngine`; confirm actual model-FD support or document the required embedding bridge.
11. Build a prototype ONNX export of PromptGuard 2 86M, tokenize with the exact upstream tokenizer, run on Android CPU and compare logits/scores against reference Transformers.
12. Benchmark primary and shadow classifiers on an English attack/benign twin corpus. Complete the model license review.
13. Prototype the exact `web_search` call through Parallel, enforce tool allowlist and reject any provider fetch tool.
14. Build a URL-fetch spike that proves strict URI validation, DNS A/AAAA checks, address pinning at the socket, TLS hostname verification, redirect inspection and response-size limits.
15. Test the staged model pipe from companion to main app, including cancellation, interrupted streams, exact hash mismatch and storage exhaustion.
16. Test image bytes on the chosen Gemma E4B model/runtime on a physical device.
17. Benchmark model load, inference, embedding and classifier on at least one 8 GB Android 15 device and one 12 GB-or-higher device.
18. Produce ADRs for all pass/fail decisions and pin the exact runtime/model/license manifests only after the evidence is complete.

### Phase 0 deliverables

- Buildable app and companion proof-of-concept.
- Host-side IPC contract and manifest integration report, explicitly separating source/configuration evidence from unverified Android runtime authorization.
- Gemma FD/JNI/runtime parity report.
- Embedding model/runtime report.
- PromptGuard ONNX/tokenizer/license report.
- Fetch SSRF proof and negative test report.
- 8 GB and 12 GB resource report.
- Image-input compatibility report.
- Signed artifact manifests and dependency/SBOM draft.
- Architecture Decision Records and revised risk register.

### Phase 0 exit gate

No full feature implementation is treated as production-bound until G1 and G2 have a viable path. G3 and G5 may remain disabled features if not ready. G4 must result in a truthful supported-device statement.

## 18. Phase 1 — Repository, app shell and CI foundation

1. Create modules around real ownership boundaries: app, domain, security, prompt, persistence/vault, file/parsers, RAG API/index/embedding, inference API/worker, guards, tools, network contract/companion and testkit.
2. Configure Kotlin, Android Gradle Plugin, Gradle, JDK and KSP versions that are mutually compatible; pin them, do not float.
3. Configure Jetpack Compose, Navigation, ViewModels, StateFlow, coroutines and structured concurrency.
4. Add JVM unit tests, host-JVM integration tests, lint, formatting and static-analysis tasks. Do not add emulator E2E or Android instrumentation jobs to CI.
5. Add merged-manifest allowlist checks; reject unexpected permissions, exported components or service declarations.
6. Add dependency verification, license inventory, SBOM generation and secret scanning.
7. Separate debug/test/release signing; keep signing keys out of the repository and CI logs.
8. Configure CI to build both app packages, run tests, audit manifests and publish test artifacts.
9. Establish deterministic test fixtures and test-only fake model/network adapters.

**Deliverable:** reproducible CI build of the shell and companion, clean permission report and test infrastructure.

## 19. Phase 2 — Vault, encrypted persistence and lifecycle

1. Design Keystore-backed key hierarchy and explicit vault lifecycle.
2. Integrate Room and SQLCipher using pinned versions.
3. Implement database migrations and test every supported schema migration.
4. Encrypt each persistent source/attachment with a separate random data key protected by the vault hierarchy.
5. Implement conversation/message persistence and deletion.
6. Implement Knowledge Library metadata tables and memory lineage schema.
7. Configure backup/data-extraction exclusions.
8. Implement biometric/device-credential gate according to the selected vault policy.
9. Lock on timeout/background according to user settings; ensure lock cancels all work and closes database/engine handles.
10. Test key invalidation, interrupted migrations, corrupted DB, deletion, restore attempts and low-storage behavior.

**Exit gate:** vault lock is enforceable; database and attachments are encrypted; deletion/revocation is complete and tested.

## 20. Phase 3 — Model manager and staged model delivery

1. Define signed model manifest with exact ID, URL host, artifact revision, filename, size, SHA-256, runtime compatibility, ABI/backend, tokenizer/template revision, license and notice.
2. Mirror only immutable artifact identifiers/allowlists in the Network Companion; no arbitrary URL input.
3. Implement model states: `NOT_INSTALLED`, `WAITING_FOR_CONSENT`, `DOWNLOADING`, `VERIFYING`, `INSTALLED`, `QUARANTINED`, `REMOVAL_PENDING`, `FAILED`.
4. Implement storage preflight, user data-network selection, download progress and cancellation.
5. Implement a bounded Binder/PFD pipe and main-app `.part` writer.
6. Verify size/hash inside the main app; atomically promote verified bytes.
7. Implement SAF import with identical validation and safe cleanup.
8. Implement interrupted-download recovery and corrupted-file quarantine.
9. Stage artifact prompts: Gemma during setup; embedding model when Knowledge Library is first activated; classifier before guarded ingestion/search context is enabled.
10. Keep model downloads separate from first-run UI where possible; explain their sizes and storage needs.

**Exit gate:** only manifest-pinned, hash-verified artifacts can transition to `INSTALLED` and become loadable.

## 21. Phase 4 — Isolated Gemma inference

1. Implement `InferenceEngine` API independent of LiteRT-LM types, plus distinct no-permission embedding and classifier worker contracts.
2. Implement the isolated Generation Worker and minimal Binder/Parcelable contracts; keep Embedding and Guard workers as separate isolated services with independent DTOs.
3. Implement the descriptor-based JNI bridge for the pinned LiteRT-LM C API.
4. Transfer read-only model FD and bounded writable cache FD; reject path-based loading.
5. Implement engine lifecycle, conversation lifecycle, token events, stop/cancel, timeout and typed failure states.
6. Add bounded context and output token budgets; do not trim system policy or source provenance to satisfy a token limit.
7. Implement serialized inference/resource scheduler.
8. Test CPU and GPU backends, low-memory shutdown, repeated load/unload and lock.
9. Add a clean fallback message when model unavailable; no hidden cloud/remote fallback.
10. Keep runtime isolation and attacker-resistance claims gated on separate device qualification; do not add emulator E2E tests to automated CI.

**Exit gate:** the exact pinned runtime loads and streams in the isolated service with no path fallback and no permission escalation.

## 22. Phase 5 — Guard stack and safe prompt serialization

1. Define typed guard interfaces and verdicts: `ALLOW_AS_UNTRUSTED`, `QUARANTINE`, `BLOCK`, `UNAVAILABLE`.
2. Implement deterministic file/content/Unicode/URL/secret/PII controls.
3. Implement the source envelope DTO and serializer, including delimiter escaping and app-generated metadata.
4. Add immutable system policy that describes the untrusted block semantics.
5. Add `ContextExposure` records for all source material included in each model call.
6. Export PromptGuard 2 86M to ONNX; test exact tokenizer and runtime parity.
7. Implement the isolated Guard Worker, supply the ONNX model via a proved descriptor or bounded-memory handoff, and implement overlapping token windows with full coverage; record model revision and classifier result per source segment.
8. Add primary-classifier thresholds calibrated on matched English attack and benign sets.
9. Run the shadow classifier offline for comparative results; do not gate runtime on it.
10. Implement quarantine UI and fail-closed behavior for model-context insertion.
11. Complete model license and redistribution review before bundling classifier weights.
12. Fuzz serialized payloads, nested wrappers, forged source metadata, invisible controls and long cross-window attacks.

**Exit gate:** no imported/external/tool-derived content reaches Gemma without current primary-guard result and safe serialization. Clean verdict never changes trust status.

## 23. Phase 6 — Document ingestion and persistent Knowledge Library

1. Implement SAF source selection and grant/revoke lifecycle.
2. Implement TXT, Markdown, JSON and CSV parsers with byte, time, depth, encoding and memory limits.
3. Implement text-based PDF parser only after PDF-specific qualification: malformed structures, page limits, hidden/invisible text, embedded files, encryption, incremental updates and extraction completeness.
4. Implement source preview, collection assignment, retention choice and persistent/ephemeral designation.
5. Implement normalized extraction records and content hashes.
6. Run deterministic guards and primary classifier before indexing.
7. Quarantine suspect documents/segments with an explainable user state; do not pass them to Gemma by default.
8. Implement chunker with versioned settings and source offsets.
9. Implement re-index, resume, cancel and source removal.
10. Implement image picker flow for transient image attachments separately; do not index images in RAG.

**Exit gate:** supported format extraction is bounded and auditable; sources cannot forge metadata or bypass the wrapper; deletion/revocation removes downstream data.

## 24. Phase 7 — Semantic RAG

1. Add EmbeddingGemma 2 text-only model manifest and staged installation.
2. Implement the isolated Embedding Worker using the proved FD boundary or a bounded-memory handoff; if neither can be made reliable, do not move embedding inference into the privileged main app while claiming full inference isolation.
3. Validate embedding prefixes, tokenizer, output dimensions and normalization.
4. Implement vector storage with model/revision/chunker/prefix identifiers.
5. Implement FTS5 schema with a tested tokenizer and content revision.
6. Implement dense cosine retrieval over authorized collection/source IDs.
7. Implement lexical FTS5 retrieval over the exact same eligible set.
8. Implement RRF fusion, deterministic tie-breaks and deduplication.
9. Implement token-aware context assembly, source citations and context-exposure lineage.
10. Implement stale-index detection, incremental re-embedding, deletion and crash recovery.
11. Build English retrieval benchmark and set release thresholds before final evaluation.
12. Measure memory, storage, indexing rate, query latency and result quality on the minimum reference device.

**Exit gate:** semantic retrieval is operational, benchmarked and constrained by source grants; no lexical-only substitute is presented as semantic RAG.

## 25. Phase 8 — Capability Broker and local tools

1. Freeze tool registry and typed request/response contracts.
2. Generate or validate strict JSON schemas and reject unknown/ambiguous fields.
3. Implement current task/session state and capability grant store.
4. Implement authorization state machine for T0–T3.
5. Implement T0 calculator/text/JSON utilities.
6. Implement T1 selected-source reads and current-task RAG retrieval.
7. Implement T2 file creation, memory edits, source deletion and settings changes with preview and fresh confirmation.
8. Bind confirmation to canonical exact payload hash, target ID, scope, issue time and expiry.
9. Implement replay protection, idempotency and audit events.
10. Test tool hallucination, cross-task IDs, forged approvals, stale confirmation, payload mutation and retry bypass.

**Exit gate:** no model output alone can cause a state change, grant or external request.

## 26. Phase 9 — Network Companion, search and restricted fetch

1. Freeze AIDL/Parcelable protocol and companion identity/signature checks.
2. Implement narrow typed `search`, `fetchPageText`, `downloadArtifact`, `cancel` and `health` methods; never expose generic HTTP.
3. Implement the keyless Parallel `web_search` call and reject any non-allowlisted MCP tool, especially provider `web_fetch`.
4. Implement optional Tavily only if the owner approves a user-supplied API key and the credential flow is encrypted and tested.
5. Implement query disclosure, secret scanner, PII warning, exact-query consent and bounded search session.
6. Parse typed results, enforce response-size/count limits, sanitize text and link rendering, classify all model-facing content.
7. Implement exact-reference fetch proposal and fresh per-URL confirmation.
8. Implement the strict URI, DNS pinning, TLS, redirect and body limits from §9.
9. Ensure fetch is no-store by default and does not recursively crawl or load subresources.
10. Add companion Play listing and install/recovery UX.
11. Test malicious provider responses, DNS rebinding, mixed address answers, redirect attacks, oversized/compressed bodies, malformed HTML, cancellation and companion compromise assumptions.

**Exit gate:** search/query boundary passes. Fetch is enabled only when connection-level SSRF proof and adversarial tests pass; otherwise `fetchPageText` is absent from the production tool registry.

## 27. Phase 10 — Complete UX and image input

1. Finalize English UI navigation and accessibility labels.
2. Implement onboarding with clear model download sizes and companion install requirement.
3. Implement Chat/Agent mode lifecycle and activity visibility.
4. Implement persistent Knowledge Library and ephemeral attachment workflows.
5. Implement vault, lock, delete-all, revoke, audit and Security screens.
6. Implement model, guard and companion state screens.
7. Implement exact search/fetch confirmation views, including URL and destination disclosure.
8. Implement image Photo Picker, safe decoding/downsampling and byte transfer to isolated inference only after G5 passes.
9. Keep locale/resource architecture ready for future Arabic without claiming Arabic support.
10. Test accessibility, font scaling, rotation, process death, navigation restoration and offline states.

**Exit gate:** every security-sensitive state is visible, cancellable and revocable; unsupported image path is not shown as available.

## 28. Phase 11 — Hardening, release candidate and Google Play publication

1. Run all JVM unit, host-JVM integration, property/fuzz and static security checks. There is no emulator E2E/instrumentation stage in CI.
2. Keep attacker-resistance, actual Binder authorization and isolated-process runtime claims as separate device-qualification evidence; host tests and manifest checks are not substitutes.
3. Audit merged manifests, exported components, signing certificates, Binder permissions and process permissions.
4. Inspect native libraries, JNI symbols, loaded files, cache access and unexpected network sockets.
5. Verify no prompt, private file, query or fetched body leaks into logs, crash output or audit trails.
6. Run device/thermal/memory matrix and define exact supported device classes.
7. Test airplane mode, companion-not-installed, provider-down, download-interrupted, model-corrupted and classifier-unavailable behavior.
8. Run static analysis, dependency vulnerability review, SBOM, license/NOTICE audit and reproducible build checks.
9. Complete independent security review and remediate every critical/high issue.
10. Freeze model/runtime/dependency revisions and build signed main/companion release packages.
11. Publish both app listings through Google Play with accurate data-safety, permissions, model-download and network-feature explanations.
12. Produce release evidence package: threat model, ADRs, SBOM, license inventory, test reports, model hashes, device matrix, known limitations and rollback plan.

**Exit gate:** all product acceptance criteria pass, no unresolved critical/high security finding remains, and every conditional feature is either qualified or disabled.

## 29. Test strategy

**Owner testing policy (r1.7):** the automated pipeline uses JVM unit tests and host-JVM integration tests only. Android emulator E2E tests, Android instrumentation source sets and emulator-runner jobs are removed. Static manifest audits and AAPT checks of assembled APKs remain part of CI. Passing host tests does not prove runtime Binder authorization, process isolation, Keystore or Android system-service behavior; keep those claims explicitly unverified until separately qualified.

**ZIP-overlay migration rule:** extracting a later project ZIP over an existing Git repository does not delete previously tracked files that are absent from that ZIP. CI therefore runs the allowlisted `scripts/cleanup_retired_emulator_assets.py` immediately after checkout in both validation and release-build jobs, before project invariants or Gradle tasks. The script removes only the retired emulator paths; the invariant checker verifies their absence afterward. The repository owner should stage and commit these deletions once to make the Git repository itself clean.


### 29.1 Unit and property tests

- Unicode normalization and legitimate joiner preservation.
- Delimiter escaping, nested untrusted wrapper attempts and forged metadata.
- Parser byte/depth/time/token limits.
- PDF hidden text and malformed-object cases.
- Chunk boundaries, source offsets and extraction completeness.
- Vector normalization, cosine scores, dimension mismatch and stale model revision.
- FTS5 query eligibility and hybrid fusion determinism.
- Secret/PII scanner false positives.
- Capability state machine, confirmation hash/expiry and replay rejection.
- URL parser, IDNA, IP special-range checks and redirect policy.
- Artifact manifest signature, byte count, SHA-256 and interrupted transfer.

### 29.2 Host-JVM integration tests (no emulator E2E)

- Main/companion source-manifest permission separation and exported-component policy.
- Signature-level permission declaration on the exported companion Binder service.
- Narrow package visibility for the two known companion package IDs.
- Shared AIDL module dependency and method-name alignment with the companion service implementation.
- Protocol-version compatibility, request validation and caller-policy state machines through deterministic fakes.
- Model manifest/hash verification, download state transitions, interrupted-transfer handling and capability-broker contracts through local fixtures/fakes.
- Packaged debug/release APK permission inspection using AAPT after Gradle assembly.
- Workflow invariants proving that CI contains no emulator runner, `androidTest` source set, `connectedAndroidTest` task or emulator E2E job.

These are host-side integration/configuration tests. They do **not** instantiate Android services and cannot prove real Binder kernel authorization, cross-UID behavior, `android:isolatedProcess`, private-file denial, SAF/Keystore behavior or Android process lifecycle. Do not report those runtime properties as verified by a passing JVM suite. They remain explicit technical qualification gates and require separate device evidence if needed.

### 29.3 Adversarial suites

- Direct and indirect instruction override in document, RAG, search result and page body.
- Fake `<untrusted>` start/end markers and forged source metadata.
- Bidi controls, invisible Unicode and malformed Unicode.
- Malicious prompt split across overlapping classifier windows.
- Benign quotations, imperative instructions, code and security education (matched twins).
- Secret and PII in outbound search requests.
- DNS rebinding, private+public mixed DNS responses, IPv4/IPv6 special addresses, IDN ambiguity and redirect tricks.
- Decompression bombs, slow responses, huge headers, malformed HTML and parser resource exhaustion.
- Model file tampering, partial downloads, manifest mismatch and disk-full conditions.
- Tool proposals with arbitrary URLs, wrong source IDs, privilege escalation, approval replay and payload mutation.

### 29.4 Evaluation metrics

- Classifier attack recall and benign false-positive rate on a versioned English matched-pair corpus.
- Reference-vs-Android classifier score/logit parity.
- RAG Recall@5/10, MRR, nDCG@10, citation correctness, groundedness and abstention quality.
- TTFT, decode tokens/sec, load time, peak RSS, PSS, battery and thermal behavior.
- Image task correctness and resource cost if image feature is enabled.
- Count of unauthorized tool invocations in test suite (report as test evidence, not proof of universal security).
- Zero sentinel-secret or private-content occurrences in logs, crash reports and audit output.

## 30. Feasibility assessment and start decision

### 30.1 Is the initial version feasible?

**Yes, with conditional scope gates.** The native Kotlin app, encrypted local persistence, persistent semantic RAG, staged model management, bounded capability broker and separately packaged network companion are all technically plausible Android engineering. The model/runtime ecosystem provides an Android Kotlin API, on-device embedding model options, multimodal content types and ONNX Runtime Android packaging. However, the full E4B isolated descriptor path and PromptGuard 2 ONNX/tokenizer integration are not established as ready-to-use official Kotlin features; both require real proof work. [R3, R4, R5, R6, R12]

The largest risk is not whether a local AI chat UI can be built. It is whether the selected combination—Gemma 4 E4B, embedding runtime, PromptGuard classifier, isolated workers and network companion—fits the memory, thermal and process constraints of the declared 8 GB baseline while preserving the promised trust boundaries.

### 30.2 Readiness verdict

**Ready to start implementation: YES — Phase 0 and the app/CI foundation.**

**Ready to implement every v0 feature without further proof: NO.**

This is not a request to pause the project. Phase 0 and the low-risk shell/vault foundations can proceed immediately. High-risk features must remain behind their gates until evidence exists.

### 30.3 Feasibility by subsystem

| Subsystem | Feasibility | Qualification still needed |
|---|---|---|
| Kotlin/Compose app and navigation | High | Normal Android engineering, CI and lifecycle tests |
| Encrypted vault and local database | High | Keystore/SQLCipher integration and key lifecycle tests |
| Gemma 4 E4B local inference | Medium–high | Actual descriptor-based isolated loading with matching v0.19.1+ ABI; device memory/thermal qualification |
| EmbeddingGemma 2 semantic RAG | High | Android model initialization, isolation compatibility, indexing quality/storage and memory |
| ONNX PromptGuard 2 86M | Medium | Exact export, tokenizer parity, CPU performance, licensing and score parity |
| Persistent hybrid RAG | High | Retrieval benchmark and source/provenance filtering |
| Separate network companion | Medium–high | Package installation UX, Binder signature checks, model streaming and protocol lifecycle |
| Search | Medium–high | Stable provider contract, rate limits, privacy screening and result guards |
| Restricted page fetch | Medium | DNS pinning at connection time, redirects, parser bounds and SSRF penetration tests |
| Image attachment | Medium | Exact Gemma E4B image path, FD/byte transfer and device memory/quality tests |
| 8 GB minimum hardware floor | Unproven | Physical-device matrix; official E4B Android benchmark is not an 8 GB minimum-device proof |
| Full production security assurance | Medium | Threat modelling, adversarial corpus, independent review and supported-device validation |

### 30.4 What can begin now

- Repository, CI, signing separation, manifest audits and dependency verification.
- Kotlin/Compose screen shell and domain interfaces.
- Threat model, source provenance DTOs, Capability Broker interfaces and testkit.
- Vault and encrypted persistence implementation, with host-side integration tests plus separately qualified Android platform behavior where required.
- Companion package skeleton and signature-protected Binder spike.
- Native inference, embedding and classifier feasibility spikes.

### 30.5 What must not be declared done yet

- Gemma E4B isolated-process loading through an official Kotlin descriptor API.
- Production classifier support from an ONNX model until score/tokenizer parity passes.
- Arabic model, RAG or guard support.
- 8 GB universal device compatibility.
- Image attachment support before exact E4B path passes.
- Restricted fetch before connection-level DNS pinning and redirect tests pass.
- Google Play AI Pack as a default delivery mechanism for the 3.65 GB E4B model.

### 30.6 Final recommendation

Proceed with Mithaq v0 as an **English-first, text-centric, image-optional, offline-capable Android app** with persistent semantic RAG and a separately installed network companion. Preserve the architecture for future Arabic but do not claim Arabic support. Keep the classifier and isolated Gemma path as early technical proofs, and ship restricted fetch/image features only when their gates pass. If a gate fails, reduce the feature set—not the security boundary.

---

# References

The following official or primary sources were checked for this revision. Version and model revisions must be rechecked when the release manifest is frozen.

- **R1 — LiteRT-LM overview and Gemma 4 E4B size/performance:** [Google AI Edge — LiteRT-LM Overview](https://developers.google.com/edge/litert-lm/overview)
- **R2 — Android isolated service permissions:** [Android Developers — `<service>` manifest element](https://developer.android.com/guide/topics/manifest/service-element)
- **R3 — LiteRT-LM Kotlin Android API and path-based `EngineConfig`:** [Google AI Edge — Get Started with LiteRT-LM on Android](https://developers.google.com/edge/litert-lm/android)
- **R4 — Runtime release and open FD feature request:** [LiteRT-LM v0.19.1 Releases](https://github.com/google-ai-edge/LiteRT-LM/releases); [LiteRT-LM issue #3905](https://github.com/google-ai-edge/LiteRT-LM/issues/3905)
- **R5 — EmbeddingGemma 2:** [Google AI — EmbeddingGemma 2 Model Card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2)
- **R6 — Android multimodal content types:** [LiteRT-LM Android Guide](https://developers.google.com/edge/litert-lm/android)
- **R7 — PromptGuard 2 86M model card, context, classification and evaluated languages:** [Meta PurpleLlama — Prompt Guard 2 86M Model Card](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Prompt-Guard-2/86M/MODEL_CARD.md)
- **R8 — PromptGuard 2 license and model access:** [Prompt Guard 2 Repository](https://github.com/meta-llama/PurpleLlama/tree/main/Llama-Prompt-Guard-2); [Hugging Face Model](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)
- **R9 — Parallel Search MCP:** [Parallel Search MCP](https://parallel.ai/mcp)
- **R10 — Tavily API authentication:** [Tavily Search API Reference](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- **R11 — Google Play On-device AI delivery limits:** [Play for On-device AI (beta)](https://developer.android.com/google/play/on-device-ai)
- **R12 — ONNX Runtime Android package:** [ONNX Runtime — Install](https://onnxruntime.ai/docs/install/)

