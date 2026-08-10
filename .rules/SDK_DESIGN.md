# SDK Design: layering, resources, pagination, errors

Load this when adding a **resource, verb, response model, or paginated listing** — anything
that grows the public surface beyond a parameter on an existing call.

This SDK is the **pilot**. The TypeScript, PHP and Ruby SDKs are expected to mirror the
decisions below, so a change here is a change to every SDK's shape. Deviating is allowed
where a language demands it (Ruby has no `TypedDict`; Go has no keyword arguments) — but the
*structure* should survive the translation, and a deliberate deviation belongs in that SDK's
own copy of this file.

## The four layers

Dependencies point inward. Nothing outer is imported by anything inner.

| Layer | Files | Job | May know about |
|---|---|---|---|
| **Client / IO** | `_client.py`, `_async_client.py` | perform one HTTP round trip | `httpx` |
| **Core** | `_base_client.py`, `_transport.py`, `_serialization.py`, `_exceptions.py` | config, URLs, headers, serialization, response parsing, error mapping | nothing I/O-specific |
| **Resources** | `_resource.py`, `resources/*.py` | the public verbs | a transport `Protocol` + spec builders |
| **Types** | `types/params.py`, `types/responses.py` | the wire contract, in and out | pydantic only |

**The load-bearing rule: all sync/async divergence lives in one method per client** (`_raw`).
`send_email` and `request` are two-liners over it; spec building, query serialization and
response parsing are shared. Everything else — every verb, every model — is written once.
This is why a two-flavour SDK stays maintainable, and it is the first thing a port should
reproduce. The duplication gate (`jscpd`, > 1% fails) exists to keep it true.

## Resources

- A resource is a **stateless namespace of verbs bound to an injected transport**. It holds
  no config, performs no I/O itself, and never imports `httpx`. Extend `Resource[TransportT]`.
- **One transport `Protocol` per capability, never one wide one.** `EmailsResource` needs
  `send_email`; it must not acquire a dependency on `request`. A new capability adds a
  protocol pair (sync + async); it does not widen an existing one.
- **Request builders are module-level functions**, one per verb (`_list_spec`, `_get_spec`, …),
  so the sync and async classes share one definition of every URL, body and query string.
  A resource method is then one line: `return self._transport.request(_get_spec(id), Model)`.
- **Async docstrings are one-line cross-references** to the sync counterpart. Duplicating the
  prose is how the two flavours start describing different behaviour.
- **Interpolated path segments are `quote(value, safe="")`-escaped.** Not cosmetic: an id
  carrying an encoded `?` or `/` otherwise re-targets the request at another route.

### Naming

- **Namespace mirrors the API resource**: `client.scheduled_emails` because the wire has a
  `scheduled-emails` collection. When the API's shape and another vendor's SDK convention
  disagree, the API wins.
- **CRUD verbs**: `list`, `get`, `update`, `cancel` (and `send`/`create` where it applies).
  These are what a developer arriving from another mail SDK guesses. Prefer them over
  domain verbs (`reschedule`) even when the domain verb reads better in isolation.
- **Sub-resources mirror sub-paths**: `scheduled-emails/batches/{id}` becomes
  `client.scheduled_emails.batches.update(batch_id, …)`, not an `update_batch` suffix.

## Response models

- **A model mirrors the wire and nothing else.** Transport metadata (headers, request ids)
  does not belong in a response model; it belongs on the exception, where a caller actually
  needs it. `Email.headers` / `.request_id` / `.idempotent_replayed` predate this rule and
  are a **grandfathered exception**, not a template — do not copy them into a new model.
- **`frozen=True, extra="ignore"`** on every model, so a server-side field addition can never
  raise in an already-released client.
- **Timestamps stay strings** — the verbatim ISO-8601 the server sent. The SDK does not
  reinterpret server data. Document `datetime.fromisoformat` for callers who want objects.
- **Accept `str | datetime` on the way in**, and render with `_serialization.to_iso`. The SDK
  makes values transmissible; it does not validate them. The server is the authority, and its
  error names are richer than anything the SDK would reproduce.
- **Keep the `object` discriminator** where the API sends one, except on `Email`, where it
  shadows a builtin on the hottest model and tells the caller nothing.
- **Widen, never union, an existing return type.** A `A | B` return is a source-breaking
  change for every existing caller under a strict type checker. When one call can return two
  shapes (an immediate send vs a scheduled ack), add optional fields plus a boolean property
  (`Email.is_scheduled`) that discriminates them.

## Pagination

- `list(**filters)` returns a **page object**: `.data`, `.pagination` (`.steps`,
  `.total_count`, `.current_page`) and a `.has_more` convenience.
- `iter_all(**filters)` returns a **lazy iterator over every page**, so the common case is one
  line and abandoning it early costs nothing. The page-advance is a pure function
  (`_next_page_spec`) shared by the sync and async generators.
- **Follow the server's `steps.next` link** rather than incrementing a page counter — the
  server stays free to change its pagination scheme.
- **Never follow a link off the configured origin.** Every request carries the
  `Authorization` header, so a link naming a foreign host would hand that host the API key.
  `BaseClient._build_url` enforces this centrally: an absolute URL is accepted only from the
  base URL's own origin, and anything else raises. Enforce it at the I/O boundary, not in the
  resource, so it protects every future link-following feature for free.
- The API **omits** a step at the ends of the range rather than sending `null`; the model
  defaults handle both.

## Errors

- **Status code chooses the exception class** (`_STATUS_EXCEPTIONS`): 400 → `BadRequestError`,
  403 → `AuthenticationError`, 404 → `NotFoundError`, 409 → `ConflictError`, 422 →
  `InvalidRequestError`, 429 → `RateLimitError`, other 5xx → `ServerError`, anything else →
  `APIError`. Do **not** add an exception subclass per server error name: that list grows
  unboundedly and ports badly.
- **The envelope's `name` is data, not a class.** `APIError.error_name` stays a plain `str` so
  a name this release has never heard of is reported verbatim instead of crashing. `ErrorName`
  provides the documented values as constants for autocomplete and comparison; because it is a
  `StrEnum`, `exc.error_name == ErrorName.QUOTA_EXCEEDED` works either way. Add a member when
  the public error reference gains a name.
- **Every error carries `request_id`** (from `X-Request-Id`) so a caller can quote a failure to
  support, and `RateLimitError` carries `retry_after`.
- **One place turns a non-2xx into an exception** (`BaseClient._ok_body`), so every verb —
  present and future — fails identically.
- A transport failure with no HTTP response is a `MailkubeConnectionError`; a 2xx body that is
  not the expected shape is a `MailkubeError`. Neither is an `APIError`.

## Checklist for a new verb

1. Params `TypedDict` in `types/params.py`, response model(s) in `types/responses.py`.
2. A module-level `_*_spec` builder in the resource module.
3. One-line sync method + one-line async method, async docstring cross-referencing the sync one.
4. Exports in `resources/__init__.py`, `types/__init__.py` and the package root, `__all__` sorted.
5. Tests: request method/URL/query/body, the parsed model, one mapped error, and the async twin.
   Branch coverage must stay ≥ 90% **line and branch**.
6. README section + an `examples/` script.
7. Run every gate in `.rules/SOLID_DRY_KISS.md` locally before pushing.
