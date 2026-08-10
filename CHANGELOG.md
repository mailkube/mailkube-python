# CHANGELOG

<!-- version list -->

## v1.4.0 (2026-08-10)

### Bug Fixes

- **events**: Allow null domain, subject, to and from on message context
  ([`156f802`](https://github.com/mailkube/mailkube-python/commit/156f802c438bc13d768ed7502fe00b55bce05df9))

### Features

- **events**: Model email.sent, email.scheduled and email.failed with message tags
  ([`156f802`](https://github.com/mailkube/mailkube-python/commit/156f802c438bc13d768ed7502fe00b55bce05df9))


## v1.3.1 (2026-08-10)

### Bug Fixes

- Ci badge link fixed
  ([`b471626`](https://github.com/mailkube/mailkube-python/commit/b471626f27b823d3c84fe7530e009f99b3d250ec))

### Chores

- **deps**: Bump ruff to 0.16.2 and format markdown code blocks
  ([`8558e05`](https://github.com/mailkube/mailkube-python/commit/8558e0554252d842d3cbaebf761ab328ce0bd916))


## v1.3.0 (2026-08-10)

### Bug Fixes

- **version**: Report the released version instead of a stale literal
  ([`0edb944`](https://github.com/mailkube/mailkube-python/commit/0edb944ea6e409a17fc595cbce3a4ec7497f0d5c))

### Features

- **scheduled**: Expose the full scheduled-email surface
  ([`93df5e1`](https://github.com/mailkube/mailkube-python/commit/93df5e10abd7dee2c6a4f6448cda6a76923f9ab5))


## v1.2.0 (2026-08-03)

### Documentation

- Document the message-tags send parameter
  ([`4805922`](https://github.com/mailkube/mailkube-python/commit/48059221909094b6217206a6674ef2f64e036efe))

### Features

- **client**: Support message tags on send
  ([`e82abc5`](https://github.com/mailkube/mailkube-python/commit/e82abc5aafdfe305ebd82b4b26e87dd13b925470))


## v1.1.1 (2026-07-26)

### Bug Fixes

- **examples**: Answer the endpoint-registration challenge in the Flask receiver
  ([`f38cfb7`](https://github.com/mailkube/mailkube-python/commit/f38cfb74838265e3b2f228b124f085ebc87c28eb))

### Chores

- **deps-dev**: Bump ruff from 0.15.21 to 0.15.22
  ([`b81f671`](https://github.com/mailkube/mailkube-python/commit/b81f67116af3245bbc3dcb9828fe557e67c7ead2))


## v1.1.0 (2026-07-17)

### Documentation

- Expand README with configuration, idempotency, logging, and examples sections
  ([`c05e6e4`](https://github.com/mailkube/mailkube-python/commit/c05e6e430bbc6105040c65e0e7502fb51c4eb513))

### Features

- Referencing mailkube's docs
  ([`24e0de9`](https://github.com/mailkube/mailkube-python/commit/24e0de93aab669ffcfb422c67922c041ab6a8131))


## v1.0.0 (2026-07-14)

- Initial Release
