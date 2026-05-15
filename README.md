# Waybill

A [Dispatcharr](https://github.com/Dispatcharr/Dispatcharr) plugin for managing channel configurations declaratively. You define a YAML manifest describing which streams to keep and how to name them; Waybill plans and applies those changes to Dispatcharr for you.

## Overview

Waybill reads a **WaybillConfig** manifest and produces a reconciled channel list inside Dispatcharr. Each run can either:

- **Plan** — preview the desired state without writing anything to the database.
- **Apply** — write the desired state to the database, in `upsert` or `overwrite` mode.

Channels are selected from Dispatcharr's stream catalogue using **matchers** and then renamed / normalised using **transformers**. Stream profiles are assigned per channel with a three-level inheritance hierarchy.

## Motivation

Some time before Dispatcharr's release, I was working on what is effectively Dispatcharr but with a much smaller scope. It would simply filter M3Us based on a pipeline to be sent to Threadfin. This was suboptimal, Threadfin was excessively memory intensive and I abandoned the project.

When Dispatcharr came along, and I saw there was a plugin system. I decided that the pipeline filtering aspect of my M3U filter API could probably be ported to Dispatcharr to allow for fully declerative channel configuration where you describe the semantics of your upstream M3U or XC playlist as YAML.

Inspired by Kubernetes YAML declaration patterns with a hint of Terraform's plan and apply functionality my goal for Waybill was to improve upon existing Dispatcharr plugins to give complete and total control to the user to define their channel layouts.

Waybill provides no mechanism for fragile matchers or transformers such as those which perform token splitting, or attempt to dynamically infer quality tags, regions, or other semantics encapsulated within names. Fuzzy search from patterns is powered by regex on a scope as limited or extensive as you like. It makes no assumptions about your stream list, you describe to Waybill how your stream list is named and it handles the rest.

### AI Disclosure

There is some Clanker output in this repository, mainly examples, documentation, unit tests and the tooling for generating the config JSON Schema. These seemed like parts there's be zero value in me writing myself.

However, almost all of the rest of the code is written by me, by hand, and then reviewed by Clankers. The config spec was designed by a human and it's interface was built with humans in mind.

## Manifest structure

```yaml
kind: WaybillConfig
version: v1alpha1
metadata:
  name: my-config
  description: Optional free-text description
spec:
  profiles:
    <profile_key>:
      name: Human-readable profile name
      streamProfile: Proxy          # optional profile-level default
      groups:
        <group_key>:
          name: Human-readable group name
          streamProfile: Redirect   # optional group-level override
          members:
            - name: Channel Name
              streamProfile: null   # optional member-level override (null clears inheritance)
              matchers:
                - ...
              transformers:
                - ...
```

### `kind` and `version`

Both fields are required. The only supported values are `WaybillConfig` and `v1alpha1`.

### Stream profile inheritance

`streamProfile` is resolved from the most specific scope that sets it:

```
member → group → profile → (none)
```

Setting `streamProfile: null` at any level explicitly clears the inherited value.

---

## Matchers

Matchers filter which streams from Dispatcharr are candidates for a channel. Multiple matchers on one member are evaluated in sequence — each one narrows (or widens, for `keep`) the candidate set.

| Type | Description |
|---|---|
| `regex` | Matches the field against a regular expression |
| `hasPrefix` | Matches if the field starts with any of the listed prefixes |
| `containsAny` | Matches if the field contains any of the listed substrings |
| `exactMatch` | Matches if the field equals any of the listed values |

All matchers share these common fields:

| Field | Default | Description |
|---|---|---|
| `field` | `name` | Stream attribute to match against (`name`, `tvg_id`, `logo_url`, …) |
| `action` | `keep` | `keep` retains matching streams; `drop` removes them |
| `caseSensitive` | `false` | Whether matching is case-sensitive |

### `regex`

```yaml
- type: regex
  field: name
  action: keep
  pattern: "^UK\\| BBC [1-9]( HD| HEVC)?$"
```

| Field | Required | Description |
|---|---|---|
| `pattern` | yes | Python regular expression |

### `hasPrefix`

```yaml
- type: hasPrefix
  field: name
  action: keep
  prefixes:
    - "UK| BBC ONE"
    - "UK| BBC One"
```

| Field | Required | Description |
|---|---|---|
| `prefixes` | yes | List of prefix strings, any of which will match |

### `containsAny`

```yaml
- type: containsAny
  field: name
  action: keep
  substrings:
    - "TALK TV"
```

| Field | Required | Description |
|---|---|---|
| `substrings` | yes | List of substrings, any of which will match |

### `exactMatch`

```yaml
- type: exactMatch
  field: name
  action: keep
  values:
    - "UK| BBC ONE HD"
    - "UK| BBC ONE HEVC"
```

| Field | Required | Description |
|---|---|---|
| `values` | yes | List of exact values, any of which will match |

### Pre-transformers

Any matcher can carry a `transformers` list. These **pre-transformers** mutate the field value *before* the matcher evaluates it, without affecting the final stream name. This is useful for normalising noisy data so a single pattern can match multiple forms:

```yaml
- type: regex
  field: name
  action: keep
  pattern: "^UK\\| BBC [1-4]( HD| HEVC)?$"
  transformers:
    - type: convertCardinalNumbers
      field: name
      outputType: number
```

---

## Transformers

Transformers rewrite stream fields after matching. They are applied in declaration order.

| Type | Description |
|---|---|
| `regex` | Replace a regex match (supports capture-group back-references) |
| `strip` | Remove a fixed prefix and/or suffix |
| `setMetadata` | Set explicit metadata fields (`name`, `logoUrl`, `tvgId`) in one step |
| `set` | Overwrite an arbitrary field with a literal value (low-level escape hatch) |
| `convertCardinalNumbers` | Convert between word and digit forms of cardinal numbers |

Transformers that target a single stream field (`regex`, `strip`, `set`, `convertCardinalNumbers`) share:

| Field | Default | Description |
|---|---|---|
| `field` | `name` | Stream attribute to transform |

### `regex`

```yaml
- type: regex
  field: name
  action: replace
  pattern: "^UK\\| "
  replacement: ""
```

| Field | Required | Description |
|---|---|---|
| `pattern` | yes | Python regular expression |
| `replacement` | yes (for `replace`) | Replacement string; use `$1`, `$2` … for back-references |
| `action` | yes | Currently only `replace` is supported |

### `strip`

```yaml
- type: strip
  field: name
  prefix: "UK| "
  suffix: " HD"
```

| Field | Required | Description |
|---|---|---|
| `prefix` | no | Literal prefix to remove if present |
| `suffix` | no | Literal suffix to remove if present |

### `set`

```yaml
- type: set
  field: name
  value: "BBC One"
```

| Field | Required | Description |
|---|---|---|
| `value` | yes | Literal value to write to the field |

`set` is intentionally low-level and can write to arbitrary fields. Prefer `setMetadata`
for common metadata assignments where field names are explicit.

### `setMetadata`

Sets one or more explicit metadata fields in a single transformer.

```yaml
- type: setMetadata
  name: "BBC One"
  logoUrl: "https://example.com/logos/bbc-one.png"
  tvgId: "bbc.one.uk"
```

| Field | Required | Description |
|---|---|---|
| `name` | no | Canonical stream name |
| `logoUrl` | no | Logo URL to write to `logo_url` |
| `tvgId` | no | TV guide identifier to write to `tvg_id` |

At least one of `name`, `logoUrl`, or `tvgId` must be provided.

### `convertCardinalNumbers`

Converts between digit and word forms of cardinal numbers (e.g. `ONE ↔ 1`).

```yaml
- type: convertCardinalNumbers
  field: name
  outputType: number
```

| Field | Values | Description |
|---|---|---|
| `outputType` | `number`, `word` | Target form to normalise to |

---

## Apply modes

| Mode | Behaviour |
|---|---|
| `upsert` | Creates or updates channels declared in the manifest; leaves any other channels untouched |
| `overwrite` | Creates or updates declared channels **and deletes** any channels that exist in a group but are not in the manifest |

---

## Examples

The `examples/` directory contains annotated manifests covering every feature:

| File | What it demonstrates |
|---|---|
| [01-minimal.yaml](examples/01-minimal.yaml) | Minimum valid manifest |
| [02-matchers.yaml](examples/02-matchers.yaml) | All four matcher types, keep/drop actions, field targeting |
| [03-transformers.yaml](examples/03-transformers.yaml) | All five transformer types including multi-step pipelines |
| [04-pre-transformers.yaml](examples/04-pre-transformers.yaml) | Transformers scoped inside a matcher |
| [05-stream-profiles.yaml](examples/05-stream-profiles.yaml) | Stream profile inheritance (profile → group → member) |
| [06-multiple-profiles.yaml](examples/06-multiple-profiles.yaml) | Multiple independent profiles in one manifest |
| [07-exhaustive.yaml](examples/07-exhaustive.yaml) | Every schema feature in one manifest |

---

## Installation

Build the plugin ZIP and install it into Dispatcharr via the plugin manager:

```sh
uv build --wheel
```

The resulting `.zip` file in `dist/` can be uploaded directly through the Dispatcharr UI.

---

## Development

```sh
# Install dependencies
uv sync

# Regenerate the JSON Schema from the Python type definitions
uv run generate_schema.py

# Run pre-commit checks
pre-commit run -a
```

The JSON Schema at `schema/config.schema.json` can be referenced by editors (e.g. VS Code with the [YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml)) to get inline validation and autocompletion when writing manifests.

Do not hand-edit `schema/config.schema.json`; always regenerate it from the source types and descriptions in `src/types/config.py` and `generate_schema.py`.
