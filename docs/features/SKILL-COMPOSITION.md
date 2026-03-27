# Skill Composition and Workflows
Author: Bogdan Ticu

## Overview

Skills can be chained together to create workflows. Users can compose skills without code.

Phase 1.5 feature (Week 5-6).

## Problem Solved

Current: Users pick one skill at a time.
Better: Connect skills into pipelines.

Example workflow:
1. Read CSV file
2. Clean and transform data
3. Generate summary
4. Save to JSON

All with no Python code.

## Workflow Format

Simple YAML declaration:

```yaml
name: data-pipeline
description: Read CSV, clean, summarize, save

skills:
  - name: csv-processor
    version: "1.0.0"

  - name: data-summarizer
    version: "1.0.0"

  - name: json-transformer
    version: "1.0.0"

steps:
  - skill: csv-processor
    function: process
    input:
      file: ${input.csv_file}
    output: raw_data

  - skill: data-summarizer
    function: summarize
    input:
      data: ${raw_data}
    output: summary

  - skill: json-transformer
    function: transform
    input:
      data: ${summary}
      operation: beautify
    output: final_result

result: ${final_result}
```

Save as: my-workflow.yaml

Run it:
```bash
skillpm workflow run my-workflow.yaml --csv_file data.csv
```

## Input and Output Contracts

Each skill declares inputs and outputs:

Skill manifest adds:

```yaml
functions:
  - name: process
    input:
      type: object
      properties:
        file:
          type: string
          description: Path to CSV file
    output:
      type: array
      items:
        type: object
      description: Parsed CSV rows
```

Workflow validates connections:
- Output of skill A matches input of skill B
- Types align
- Required fields present
- Errors caught before run

## Error Handling

If a step fails:

```yaml
error_handling: stop  # stop or continue

retry:
  on_failure: 2
  delay_seconds: 5

timeout_seconds: 300
```

Options:
- stop: Abort entire workflow
- continue: Skip failed step
- retry: Attempt N times with delay

Failed step logged with context.

## Sharing Workflows

Workflows can be published:

```bash
skillpm workflow publish my-workflow.yaml \
  --description "Clean and summarize CSV" \
  --author "John Doe"
```

Then others can use:
```bash
skillpm workflow run shared:john-doe/csv-pipeline
```

Works like skills: searchable, versioned, rated.

## Complex Workflows

Conditional execution:

```yaml
steps:
  - skill: sentiment-analyzer
    function: analyze
    input:
      text: ${input.comment}
    output: sentiment

  - skill: email-summarizer
    function: summarize
    input:
      email: ${input.email}
    output: summary
    if: ${sentiment.sentiment == "negative"}
    description: Only summarize if sentiment is negative
```

Loops:

```yaml
steps:
  - skill: csv-processor
    function: process
    input:
      files: ${input.csv_list}
    output: results
    foreach: file in input.csv_list
    description: Process each CSV file
```

Parallel execution:

```yaml
parallel:
  - skill: image-metadata
    input: ${input.image1}
    output: meta1

  - skill: image-metadata
    input: ${input.image2}
    output: meta2

result:
  - ${meta1}
  - ${meta2}
```

## Composition Limits

Phase 1.5:
- Simple sequences (no branching)
- No loops yet
- No parallel
- Max 10 steps

Phase 2:
- Conditionals
- Loops
- Parallel steps
- Nested workflows

## Creator Analytics for Workflows

Dashboard shows:
- Runs per week
- Success rate
- Average runtime
- Errors encountered
- User feedback

Authors see what works, what breaks.

## Example Workflows

### Extract and Format
```yaml
steps:
  - skill: article-summarizer
    function: summarize
    input: article_text
    output: summary

  - skill: markdown-processor
    function: to_html
    input: summary
    output: html_page

result: html_page
```

### Code Review Pipeline
```yaml
steps:
  - skill: code-formatter
    function: detect_language
    input: code
    output: language

  - skill: code-reviewer
    function: review
    input: code
    output: issues

  - skill: code-reviewer
    function: security_check
    input: code
    output: warnings

result:
  issues: ${issues}
  warnings: ${warnings}
```

### Data Transformation
```yaml
steps:
  - skill: csv-processor
    function: process
    input: file
    output: rows

  - skill: json-transformer
    function: transform
    input: rows
    operation: flatten
    output: flat_data

  - skill: json-transformer
    function: validate
    input: flat_data
    output: validated

result: validated
```

## Future Enhancements

Phase 2+:
- Visual workflow editor
- Workflow templates
- Version management
- Dependency resolution
- Advanced debugging
- Performance profiling
- Cost estimation

## Benefits

For users:
- Complex tasks without code
- Reusable templates
- Transparency (see each step)
- Easy to debug

For ecosystem:
- Increases skill value
- Creates network effects
- Community contributions
- More use cases discovered
