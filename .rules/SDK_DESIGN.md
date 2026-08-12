# SDK Design: the Python realization of the cross-SDK contract

Load this alongside [`SDK_CONTRACT.md`](SDK_CONTRACT.md) when adding a **resource, verb, response
model, paginated listing, or webhook event**.

`SDK_CONTRACT.md` is the shared, language-neutral constitution: configuration, layering, naming,
response-model rules, pagination, the error model, and the webhook contract, all of which every
mailkube SDK implements identically. It is synced from `repo-template/common/` and must not be
edited here.

**This file covers only what is specific to Python**: the module layout, the chosen libraries, the
sync/async rule, and the typing idioms that realize the contract. This SDK is the **pilot**, so the
shapes below are what the other SDKs translate. A deliberate deviation belongs in that SDK's own
copy of this file, never in the shared contract.

## The four layers, in files

| Layer | Files | May know about |
|---|---|---|
| **Client / IO** | `_client.py`, `_async_client.py` | `httpx` |
| **Core** | `_base_client.py`, `_transport.py`, `_serialization.py`, `_exceptions.py` | nothing I/O-specific |
| **Resources** | `_resource.py`, `resources/*.py` | a transport `Protocol` + spec builders |
| **Types** | `types/params.py`, `types/responses.py`, `types/events.py` | pydantic only |

Runtime dependencies are `httpx` and `pydantic`, and nothing else. `httpx` appears in exactly two
modules; a resource that imports it is a bug.

**The load-bearing rule: all sync/async divergence lives in one method per client** (`_raw`).
`send_email` and `request` are two-liners over it; spec building, query serialization and response
parsing are shared. Everything else, every verb and every model, is written once. This is why a
two-flavour SDK stays maintainable, and it is the first thing a port should reproduce. The
duplication gate (`jscpd`, over 1% fails) exists to keep it true.

## Python idioms that realize the contract

- **The narrow transport interfaces are `Protocol`s**, in `_transport.py`, one sync/async pair per
  capability (`SendTransport`/`AsyncSendTransport`, `ScheduledTransport`/`AsyncScheduledTransport`).
  Structural typing, not ABCs. A new capability adds a pair; it never widens an existing one.
- **The resource base is a PEP 695 generic**, `class Resource[TransportT]`, parameterized by the
  narrow protocol each resource needs: `Resource[SendTransport]`, `Resource[ScheduledTransport]`.
- **Request builders are module-level functions** in the resource module (`_list_spec`, `_get_spec`,
  `_cancel_spec`, `_next_page_spec`), so the sync and async classes share one definition of every
  URL, body and query string. A resource method is then one line:
  `return self._transport.request(_get_spec(id), Model)`.
- **Both flavours of a resource live in the same module**, so they cannot drift apart and cannot
  duplicate the spec builders.
- **Async docstrings are one-line cross-references** to the sync counterpart. Duplicating the prose
  is how the two flavours start describing different behaviour.
- **Params are `TypedDict` + PEP 692 `Unpack`**, so keyword autocomplete and static checking survive
  the `**params` indirection. Nothing in `types/params.py` is validated at runtime: the server is
  the authority.
- **Responses are frozen pydantic v2 models** (`frozen=True, extra="ignore"`), with
  `extra="allow"` on the inbound event models per the contract's webhook inversions.
- **Interpolated path segments use `quote(value, safe="")`** (see `_item_path`).
- **`ErrorName` is a `StrEnum`**, so `exc.error_name == ErrorName.QUOTA_EXCEEDED` works whether the
  caller compares against the enum or a bare string, while `APIError.error_name` stays a plain
  `str`.
- **`_KNOWN_TAGS` is derived from the `WebhookEvent` union by `_union_tags()`**, so the set and the
  union cannot disagree. Do not reintroduce a hand-maintained list: a tag missing from it routes a
  wired-up event to `UnknownEvent` with no test failure.
- **`Literal` is only ever used for SDK-controlled discriminators**, never for a server-controlled
  string.
- `from __future__ import annotations` at the top of every module; mypy strict over `src`.

## Where the shared rules are enforced

| Contract rule | Enforced in |
|---|---|
| Key/base-URL resolution, default headers | `BaseClient.__init__`, `BaseClient._default_headers` |
| Origin guard and URL joining | `BaseClient._build_url` |
| One place maps non-2xx to an exception | `BaseClient._ok_body` calling `raise_for_response` |
| Status-to-class table | `_STATUS_EXCEPTIONS` in `_exceptions.py` |
| Idempotency-key and wire-name lifting | `_HEADER_PARAMS` / `_WIRE_RENAMES` in `_base_client.py` |
| ISO-8601 rendering, query encoding, attachments | `_serialization.py` |
| Version from package metadata | `_version.py` (`importlib.metadata`), asserted in `tests/test_package.py` |
| Header redaction | `_logging.py` |
| HTTP client injection and ownership | `http_client=` on both clients, `self._owns_http` |
| Concurrency safety, proven not asserted | `tests/test_concurrency.py` |

## Grandfathered exceptions

`Email.headers`, `Email.request_id` and `Email.idempotent_replayed` carry transport metadata on a
response model, which the contract forbids. They predate the rule and are kept for compatibility.
**Do not copy them into a new model**: transport metadata belongs on the exception.

`Email` also drops the `object` discriminator the API sends, because it shadows a builtin on the
hottest model and tells the caller nothing. Keep the discriminator everywhere else.

## Tests

The DI seam is the test seam: `tests/conftest.py` builds clients over `httpx.MockTransport`, so the
suite makes zero network calls. `conftest.py` is a plain importable helper module, not a fixture
file (`from conftest import make_client, ok_handler`).

Async tests call `asyncio.run()` inside ordinary sync test functions, which is why there is no
`pytest-asyncio` dependency.

**`tests/test_concurrency.py` is the contract's concurrency proof, and it brings its own transports
on purpose.** `conftest`'s `capturing_handler` writes into one shared dict, so a concurrent test
built on it would race in the *helper* rather than in the client. Both transports hold every request
at a barrier until all thirty-two have arrived: that proves the calls really overlap (a client that
serialized them would never fill the barrier) and releases every caller in the same instant so their
continuations contend. Do not replace the barrier with per-request sleeps. That was the first draft,
and when the client was broken on purpose the sync test went red while the async one stayed green:
with replies arriving one at a time only a single task is ever runnable, so it resumes and reads its
own state back before anything can clobber it.

Guards worth preserving when adding surface: the parametrized status-to-exception table test,
`test_catalogue_matches_the_union` and its `set(PAYLOADS) == _KNOWN_TAGS` assertion,
`test_public_symbols_are_exported` walking `__all__`, `test_version_matches_the_installed_distribution`,
and `test_py_typed_marker_ships`.

## Python specifics for the contract checklists

`SDK_CONTRACT.md` carries the canonical checklists for a new verb and a new webhook event. In this
repo they land in these files:

- **New verb**: params `TypedDict` in `types/params.py`, models in `types/responses.py`, `_*_spec`
  builder in the resource module, one-line sync + async methods, exports in `resources/__init__.py`,
  `types/__init__.py` and the package root with `__all__` sorted, tests including the async twin,
  a README section and an `examples/` script.
- **New webhook event**: context block and `*Data`/envelope classes in `types/events.py`, one union
  arm on `WebhookEvent` before the `UnknownEvent` arm, exports in `types/__init__.py` and the
  package root (envelope only), a `PAYLOADS` entry plus the expected tag in
  `tests/test_webhooks.py`, and a row in the README event-types table.

Coverage must stay at or above 90% **line and branch**. Run every gate in
`.rules/SOLID_DRY_KISS.md` locally before pushing.
