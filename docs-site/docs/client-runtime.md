---
sidebar_position: 6
---

# Browser client (`/_kindling/client.js`)

The script is **bundled** with **Idiomorph** (id-aware morphing). It is mounted the first time a `LivePage` is registered.

## Config

A JSON blob in `#kindling-live-config` describes:

- `path` - LivePage path
- `bindings` - map of element id to list of events (`click`, `submit`, ...)
- `reactiveUrl` - optional SSE URL for `@bind` / `@live`

## POST + morph

For same-path POSTs initiated by bound forms or elements, the client:

1. Prevents default navigation.
2. POSTs `application/x-www-form-urlencoded` with `X-Requested-With: kindling-live`.
3. Replaces `document.body` content via **Idiomorph.morph** (innerHTML style) against a parsed response document.
4. Re-runs **inline** scripts by replacing `script` nodes (so one-time `window` listeners should be guarded).
5. Re-reads config and reconnects **EventSource** when `reactiveUrl` changes.

**Duplicate** loads of `/_kindling/client.js` are suppressed during morph via `beforeNodeAdded`.

## SSE

When `reactiveUrl` is set, the client maintains an **EventSource**. Each message updates bound nodes from `binds` and dispatches `kindling-live` when `live` is non-empty.

## Forms

- Forms with `method="post"` whose action resolves to the **current** path may be intercepted.
- If the form `id` is listed under `bindings` with `submit`, the client adds `kindling_target` and `kindling_event=submit`.

## Buttons

Elements with `data-kindling-action` POST `action=<name>` for named `LivePage.action` handlers.
