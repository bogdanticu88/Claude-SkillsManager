package tests

import (
	"testing"

	"github.com/skillpm/skillpm/pkg/manifest"
)

func TestValidateValidManifest(t *testing.T) {
	yamlContent := []byte(`
name: test-skill
version: 1.0.0
author: test-author
description: A test skill
license: MIT
entry_point: main.py
language: python
target_llms:
  - claude
`)

	err := manifest.Validate(yamlContent)
	if err != nil {
		t.Fatalf("Expected valid manifest, got error: %v", err)
	}
}

func TestValidateInvalidManifest(t *testing.T) {
	yamlContent := []byte(`
name: INVALID_NAME
version: 1.0
author: test-author
# missing required fields
`)

	err := manifest.Validate(yamlContent)
	if err == nil {
		t.Fatal("Expected invalid manifest to fail validation")
	}
}

func TestLoadManifest(t *testing.T) {
	yamlContent := []byte(`
name: test-skill
version: 1.0.0
author: test-author
description: A test skill
license: MIT
entry_point: main.py
language: python
target_llms:
  - claude
`)

	m, err := manifest.Load(yamlContent)
	if err != nil {
		t.Fatalf("Expected to load manifest, got error: %v", err)
	}

	if m.Name != "test-skill" {
		t.Errorf("Expected name 'test-skill', got '%s'", m.Name)
	}
}
