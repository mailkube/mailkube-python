# SDK Contract: the decisions every mailkube SDK implements identically

Load this when adding a **resource, verb, response model, paginated listing, or webhook event**,
or when wiring a framework integration to the mailkube API.

This file is **language-neutral and shared**. It lives in `common/.rules/` in the `repo-template`
repo and is synced verbatim into every SDK, so all of them describe one API the same way. Do not
edit a synced copy: edit `common/.rules/SDK_CONTRACT.md` in `repo-template` and run `make sync`.

The *structure* below must survive translation into any language. Where a language genuinely
demands a different shape (no keyword arguments, no structural typing, no async), the deviation is
allowed but must be **recorded in that SDK's own `.rules/SDK_DESIGN.md`**, which is where the
language-specific realization lives.

## Configuration

Identical in every SDK. A caller who learns one SDK knows them all.

| Concern | Contract |
|---|---|
| Auth | `Authorization: Bearer <key>` |
| Key resolution | constructor argument, then `MAILKUBE_API_KEY`, then raise |
| Base URL | constructor argument, then `MAILKUBE_BASE_URL`, then `https://api.mailkube.com/mta/v1/` (trailing slash) |
| Timeout | 30 seconds, configured per client, not per call |
| Retries | **None.** See below |
| Idempotency | an `idempotency_key` parameter lifts out of the body into an `Idempotency-Key` header; the response reports whether the request was replayed |
| User-Agent | `mailkube-<lang>/<version>` |
| Request id | read `X-Request-Id` off every response and attach it to errors |

**The version has exactly one source of truth, and the User-Agent reads that source.** What counts
as the source is the language's own convention: installed package metadata where the manifest owns
the version (Python, Node, Go, PHP), or a version constant that the manifest itself reads where that
is the idiom (Ruby's `lib/<gem>/version.rb`). What is forbidden is a **second** copy that release
tooling can bump independently. This is not hypothetical: the Python SDK reported
`mailkube-python/0.1.0` for releases 1.0.0 through 1.2.0 because the source carried a literal
alongside the manifest.

Where the metadata route can legitimately return nothing — a package running from a build tree
rather than an installed artifact, which is the normal case in tests and IDEs — fall back to a
documented placeholder such as `0.0.0` rather than failing or emitting an empty version.

**There are no built-in retries.** Surface what the caller needs to decide for themselves: the
retry-after value on a rate-limit error, and a server-error class documented as safe to retry with
backoff. A retry loop hidden inside the SDK turns one caller-visible failure into an unbounded
delay, and it silently re-sends non-idempotent requests. Idempotency keys are the retry story.

## Layering

Dependencies point inward. Nothing outer is imported by anything inner.

| Layer | Job | May know about |
|---|---|---|
| **Client / IO** | perform one HTTP round trip | the HTTP library |
| **Core** | config, URL building, headers, serialization, response parsing, error mapping | nothing I/O-specific |
| **Resources** | the public verbs | a narrow transport interface plus request builders |
| **Types** | the wire contract, inbound and outbound | the model/serialization library only |

## Client flavours and concurrency

How many clients an SDK ships is decided by the **language**, not by preference. Pick the rule that
applies and record the outcome in that SDK's own `.rules/SDK_DESIGN.md`:

- **Async only**, where the language has no synchronous HTTP. There is nothing to choose.
- **A sync and an async client**, where both are first-class and callers genuinely need both. The
  async flavour is named by prefixing the sync one (`Mailkube` and `AsyncMailkube`), and the two
  surfaces stay verb-for-verb identical.
- **Sync only**, where concurrency is the caller's concern rather than an API-surface decision, or
  where async would mean depending on something outside the language's standard interfaces. Give the
  caller the control they need instead: a per-call cancellation or deadline handle.

Current realizations: Python ships both; Node is async only; Go and PHP are sync only.

**Shipping one client is not the same as being single-threaded.** Where the flavour is sync only
because concurrency is the caller's concern, the SDK is making a promise about what the caller may
do with it, and that promise needs the guarantee below behind it.

### Concurrency safety is required, and tested

**Whatever the flavour, one client instance is safe for concurrent use, and a test proves it.** What
"concurrent" means is the language's own answer: goroutines in Go, threads (and fibers, where a
scheduler is installed) in Ruby, virtual threads in Java, tasks on the loop in Python and Node.

**The test asserts more than "no exception was raised". It asserts that concurrent calls do not
observe each other's responses.** This is the failure that matters and the one a naive test misses.
A client that shares one mutable connection across callers does not usually crash: two callers
interleave on the same socket and one receives the other's response body. Inside a single process
that is a confidentiality bug, not a flaky test, and it will pass any assertion weaker than this one.

The practical shape: issue N concurrent calls whose requests are distinguishable from each other,
have the stub or test server echo each request's distinguishing value back in its response, then
assert every response carries **its own** call's value. Prove the test works by deliberately
breaking the client once and watching it fail.

A client that reaches this bar holds no mutable per-request state after construction. Freezing or
otherwise sealing the client where the language allows it turns a whole class of future regression
into a compile or test failure.

**Where an SDK ships both, all divergence between them lives in exactly one method per client.**
Every verb, every model, every query-string rule is written once. This is the first thing a port
should reproduce, and the duplication gate (`jscpd`, over 1% fails) exists to keep it true. A
secondary flavour that grows its own request building will pass its tests and drift from the primary
one silently, which is the failure this rule exists to prevent.

**A framework integration inherits the flavour of the framework's extension point, not of the SDK it
wraps.** Where the framework hook is synchronous, the integration is synchronous even if the
underlying SDK offers an async client, and it must not start an event loop to reach it.

## Resources

- A resource is a **stateless namespace of verbs bound to an injected transport**. It holds no
  config, performs no I/O itself, and never imports the HTTP library.
- **One narrow transport interface per capability, never one wide one.** The emails resource needs
  to send an email; it must not acquire a dependency on every other verb. A new capability adds an
  interface; it does not widen an existing one.
- **Request builders are standalone functions**, one per verb, so every flavour of a client shares
  one definition of each URL, body and query string. A resource method is then one line.
- **Interpolated path segments are URL-escaped.** Not cosmetic: an identifier carrying an encoded
  `?` or `/` otherwise re-targets the request at a different route.

### Naming

- **The namespace mirrors the API resource.** The wire has a `scheduled-emails` collection, so the
  SDK exposes `scheduled_emails` (in that language's casing). When the API's shape and another
  vendor's SDK convention disagree, the API wins.
- **CRUD verbs**: `list`, `get`, `update`, `cancel`, and `send`/`create` where they apply. These are
  what a developer arriving from another mail SDK guesses. Prefer them over domain verbs
  (`reschedule`) even when the domain verb reads better in isolation.
- **Sub-resources mirror sub-paths.** `scheduled-emails/batches/{id}` becomes a nested
  `scheduled_emails.batches.update(id, ...)`, not an `update_batch` suffix.

## Response models

- **A model mirrors the wire and nothing else.** Transport metadata (headers, request ids) belongs
  on the exception, where a caller actually needs it, not on a response model.
- **Immutable, and unknown fields are ignored.** A server-side field addition must never raise in an
  already-released client.
- **Timestamps stay verbatim strings**, exactly as the server sent them. The SDK does not
  reinterpret server data. Document the language's parse function for callers who want objects.
- **Accept either a string or the language's datetime type on the way in**, and render to ISO-8601
  through the one shared serializer. The SDK makes values transmissible; it does not validate them.
  The server is the authority and its error names are richer than anything the SDK would reproduce.
- **Widen, never union, an existing return type.** Returning `A | B` where callers previously got
  `A` is a source-breaking change under any strict type checker. When one call can return two
  shapes, add optional fields plus a boolean property that discriminates them.

## Pagination

- A list verb returns a **page object**: the data array, the pagination block, and a convenience
  flag for whether more pages exist.
- An **iterate-all verb returns a lazy iterator over every page**, so the common case is one line
  and abandoning it early costs nothing. The page-advance is a pure function shared by every client
  flavour.
- **Follow the server's `next` link** rather than incrementing a page counter, so the server stays
  free to change its pagination scheme.
- **Never follow a link off the configured origin.** Every request carries the `Authorization`
  header, so a link naming a foreign host would hand that host the API key. Enforce this centrally
  at the I/O boundary, not in the resource, so it protects every future link-following feature for
  free.
- The API **omits** a step at the ends of the range rather than sending null; model defaults handle
  both.

## Errors

Every SDK exposes one base error type. Below it sit a transport-failure type (no HTTP response was
received), a webhook signature-verification type, and an API error type carrying the server's
`{name, message, statusCode}` envelope.

**The status code chooses the API error subclass:**

| Status | Class |
|---|---|
| 400 | BadRequest |
| 403 | Authentication |
| 404 | NotFound |
| 409 | Conflict |
| 422 | InvalidRequest |
| 429 | RateLimit (carries the retry-after value) |
| other 5xx | Server |
| anything else | the base API error |

- **Do not add an error subclass per server error name.** That list grows unboundedly and ports
  badly.
- **The envelope's `name` is data, not a class.** It stays a plain string, so a name this release
  has never heard of is reported verbatim instead of crashing. Provide the documented values as
  constants for autocomplete and comparison, and add one when the public error reference gains a
  name.
- **Every error carries the request id** so a caller can quote a failure to support.
- **Exactly one place turns a non-2xx into an error**, so every verb, present and future, fails
  identically.
- A transport failure with no HTTP response is **not** an API error. Neither is a 2xx body that is
  not the expected shape.

## Webhooks

Signature scheme, identical everywhere: HMAC-SHA256 over the webhook id, a literal `.`, the
timestamp, another `.`, then the **raw request body**, hex-encoded, sent as
`X-Webhook-Sig: sha256=<hex>`. Compare in constant time. Reject timestamps outside a 300 second
freshness window. Verification uses only the language's standard library and needs no client
instance.

Inbound event models follow the response-model rules with two deliberate inversions, both so a
released client never raises on a payload it has not seen:

- **Unknown fields are preserved, not dropped**, so a receiver logging or forwarding an event keeps
  fields this version predates.
- **An unknown event type is a valid parse result, not an error.** Any type outside the known set
  degrades to untyped access instead of breaking event parsing.

**The event union is the catalogue.** Derive the known-type set from the union rather than
hand-maintaining a parallel list: a type missing from a hand-maintained list routes a wired-up event
to the unknown arm with no test failure.

Server-controlled strings (`reason`, `status`, `disabled_reason`) stay plain strings. A closed enum
turns a new server-side value into a parse error on an already-released client.

## Logging

Silent by default. Provide an opt-in enable function and honour a `MAILKUBE_LOG` environment
variable. **Redact the `authorization` and `idempotency-key` headers** wherever headers are logged.

## Testability

The HTTP client is **injectable through the constructor**, and the SDK does not close a client it
did not create. This is a dependency-inversion seam first and a test seam second: it is what lets
the whole suite run with zero network access, by injecting a stub transport that asserts on the
request and returns a canned response.

## Checklist for a new verb

1. Request parameter type and response model(s) in the types layer.
2. A standalone request-builder function in the resource module.
3. A one-line method per client flavour; a secondary flavour's doc comment cross-references the
   primary one rather than duplicating the prose, which is how two flavours start describing
   different behaviour.
4. Exports updated everywhere the language requires, kept sorted.
5. Tests: request method, URL, query and body; the parsed model; one mapped error; and the twin for
   every other client flavour.
6. A README section and a runnable script in `examples/`.
7. Run every gate in `.rules/SOLID_DRY_KISS.md` locally before pushing.

## Checklist for a new webhook event

1. A context block for the nested object, **only if no existing one fits**. Events reuse a context
   when the server reuses the same serializer.
2. A data class plus an envelope class declaring the type discriminator.
3. One arm on the event union, before the unknown arm. That is the whole registration.
4. Exports updated, kept sorted.
5. A payload fixture in the webhook tests, which the parametrized parse test and the
   catalogue-matches-the-union guard both pick up, plus a field-level assertion per nested block.
6. A row in the README event-types table.
7. Run every gate in `.rules/SOLID_DRY_KISS.md` locally before pushing.
