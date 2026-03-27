# Breaking Change Detection
Author: Bogdan Ticu

## Overview

When skills update, detect what breaks. Warn users before upgrading.

Phase 2 feature.

## Problem

Skill v1.0:
```python
def analyze(text):
    return {
        "sentiment": "positive",
        "score": 0.9
    }
```

Skill v2.0 (breaking):
```python
def analyze(text):
    return {
        "result": "positive",    # Field renamed
        "confidence": 0.9        # Field renamed
    }
```

Old code breaks. User doesn't know until it fails.

Better: Detect and warn before upgrade.

## Solution

Manifest declares input and output schemas:

```yaml
functions:
  - name: analyze
    input:
      type: object
      properties:
        text:
          type: string
          required: true

    output:
      type: object
      properties:
        sentiment:
          type: string
          enum: [positive, negative, neutral]
        score:
          type: number
          minimum: 0
          maximum: 1
      required: [sentiment, score]
```

CLI detects breaking changes:

```bash
skillpm validate version-upgrade \
  --from sentiment-analyzer:1.0.0 \
  --to sentiment-analyzer:2.0.0

BREAKING CHANGES DETECTED:

Output Schema Changed:
- Field removed: sentiment
- Field removed: score
- Field added: result
- Field added: confidence

Impact: 3 workflows broken
  - email-pipeline
  - content-review
  - feedback-analyzer

Action Required:
1. Update skill or workflow
2. Contact skill author
3. Downgrade if incompatible

Proceed? (y/n)
```

## Schema Format

Input schema:

```yaml
input_schema:
  type: object
  properties:
    file:
      type: string
      description: "Path to file"
    options:
      type: object
      properties:
        format:
          type: string
          enum: [json, csv, xml]
  required: [file]
```

Output schema:

```yaml
output_schema:
  type: object
  properties:
    rows:
      type: array
      items:
        type: object
    metadata:
      type: object
      properties:
        row_count:
          type: integer
        columns:
          type: array
  required: [rows]
```

## Breaking vs Non-Breaking

Breaking changes:
- Output field removed
- Output type changed (string to int)
- Required input field added
- Input field type changed
- Enum values removed

Non-breaking changes:
- New optional output field
- New optional input field
- Enum value added
- Default value changed
- Description changed
- Performance improvement

## Detection Algorithm

For each version:

1. Parse old manifest (v1.0)
2. Parse new manifest (v2.0)
3. Compare schemas
4. Generate change report
5. Classify as breaking/safe
6. Find impacted workflows

```python
def detect_breaking_changes(old_schema, new_schema):
    changes = []

    # Check output fields
    for field in old_schema.output.properties:
        if field not in new_schema.output.properties:
            changes.append({
                "type": "breaking",
                "change": f"Output field '{field}' removed"
            })
        else:
            # Check type match
            old_type = old_schema.output.properties[field].type
            new_type = new_schema.output.properties[field].type
            if old_type != new_type:
                changes.append({
                    "type": "breaking",
                    "change": f"Output field '{field}' type changed"
                })

    # Check required inputs
    for field in new_schema.input.required:
        if field not in old_schema.input.required:
            changes.append({
                "type": "breaking",
                "change": f"Input field '{field}' now required"
            })

    return changes
```

## Workflow Impact Analysis

Find workflows using this skill:

```bash
skillpm analyze-impact sentiment-analyzer:1.0.0

Workflows using this skill:
1. email-pipeline
   - Function: analyze()
   - Uses fields: sentiment, score
   - Status: BROKEN (fields removed in v2.0)

2. content-review
   - Function: analyze()
   - Uses fields: sentiment, score
   - Status: BROKEN (fields removed in v2.0)

3. feedback-analyzer
   - Function: analyze()
   - Uses fields: sentiment, score
   - Status: BROKEN (fields removed in v2.0)

Impact: 3 workflows broken by v2.0 update
```

## Migration Assistance

For breaking changes, help users migrate:

```yaml
breaking_change_migration:
  version_from: 1.0.0
  version_to: 2.0.0
  changes:
    - field_renamed:
        old: sentiment
        new: result
    - field_renamed:
        old: score
        new: confidence

migration_guide: |
  Update your code:
  - Change 'sentiment' to 'result'
  - Change 'score' to 'confidence'
  All other behavior unchanged.
```

Shown to users during update.

## Version Compatibility Matrix

Show what's compatible:

```
Workflows using sentiment-analyzer:

Workflow              v1.0.0  v1.1.0  v2.0.0
email-pipeline         ✓       ✓       ✗
content-review         ✓       ✓       ✗
feedback-analyzer      ✓       ✓       ✗

Key:
✓ Compatible
✗ Breaking change
⚠ Warning
```

Users choose compatible versions.

## Deprecation Path

Mark fields for future removal:

```yaml
output_schema:
  properties:
    sentiment:
      type: string
      deprecated: true
      deprecated_since: 1.5.0
      removed_in: 2.0.0
      migration: "Use 'result' instead"
```

Workflow:
1. v1.5: Mark deprecated
2. v2.0: Remove field
3. Users warned in v1.5
4. Break in v2.0 is expected

## Testing

Test schemas work:

```bash
skillpm test-schema <skill>

Test input:
{
  "text": "This is great!"
}

Expected output:
{
  "sentiment": "positive",
  "score": 0.9
}

✓ Schema matches
✓ Types correct
✓ Required fields present
```

## Registry Validation

Registry checks before publishing:

```
Publishing sentiment-analyzer:2.0.0

Validation:
✓ Code compiles
✓ Tests pass
✓ Security check passed
✓ Schema validated

Breaking Changes Detected:
- Output fields removed: 2
- Input behavior changed: No

Workflows affected: 3

Confirm to publish with warnings? (y/n)
```

Author must acknowledge impact.

## User Workflow

```bash
skillpm install sentiment-analyzer

# User code
result = sentiment.analyze("Great!")
sentiment_value = result["sentiment"]

# Later, author releases v2.0.0
skillpm update

# CLI detects breaking change
Breaking Change Detected!

sentiment-analyzer 2.0.0 has breaking changes:
- Output field 'sentiment' removed
- Use 'result' instead

Your code will break.

Choices:
1. Update to 2.0.0 (manual code changes needed)
2. Stay on 1.0.0 (no updates)
3. Pin to 1.x (get non-breaking updates)

Choose: 3
```

## Future Enhancements

- Auto-migration tools
- Semantic versioning enforcement
- Stability guarantees
- Long-term support versions
- Deprecation schedules
