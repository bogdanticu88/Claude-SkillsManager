package manifest

import (
	_ "embed"
	"encoding/json"
	"fmt"

	"github.com/xeipuuv/gojsonschema"
	"gopkg.in/yaml.v3"
)

//go:embed skill.schema.json
var schemaData []byte

func Validate(yamlContent []byte) error {
	var manifestData interface{}
	err := yaml.Unmarshal(yamlContent, &manifestData)
	if err != nil {
		return fmt.Errorf("failed to parse YAML: %w", err)
	}

	// Convert to JSON to use JSON Schema validator
	jsonContent, err := json.Marshal(manifestData)
	if err != nil {
		return fmt.Errorf("failed to convert YAML to JSON: %w", err)
	}

	schemaLoader := gojsonschema.NewBytesLoader(schemaData)
	documentLoader := gojsonschema.NewBytesLoader(jsonContent)

	result, err := gojsonschema.Validate(schemaLoader, documentLoader)
	if err != nil {
		return fmt.Errorf("failed to validate manifest: %w", err)
	}

	if !result.Valid() {
		var errMsgs string
		for _, desc := range result.Errors() {
			errMsgs += fmt.Sprintf("- %s\n", desc)
		}
		return fmt.Errorf("manifest is invalid:\n%s", errMsgs)
	}

	return nil
}

func Load(yamlContent []byte) (*Manifest, error) {
	if err := Validate(yamlContent); err != nil {
		return nil, err
	}

	var m Manifest
	if err := yaml.Unmarshal(yamlContent, &m); err != nil {
		return nil, fmt.Errorf("failed to unmarshal manifest: %w", err)
	}

	return &m, nil
}
