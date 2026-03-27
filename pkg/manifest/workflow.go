package manifest

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"gopkg.in/yaml.v3"
)

//go:embed workflow.schema.json
var workflowSchema []byte

type WorkflowStep struct {
	Name     string          `yaml:"name" json:"name"`
	Skill    string          `yaml:"skill" json:"skill"`
	Input    string          `yaml:"input,omitempty" json:"input,omitempty"`
	Output   string          `yaml:"output,omitempty" json:"output,omitempty"`
	If       string          `yaml:"if,omitempty" json:"if,omitempty"`
	Parallel bool            `yaml:"parallel,omitempty" json:"parallel,omitempty"`
	OnError  *OnErrorPolicy `yaml:"on_error,omitempty" json:"on_error,omitempty"`
}

type OnErrorPolicy struct {
	Action     string `yaml:"action" json:"action"` // retry, skip, fail
	RetryCount int    `yaml:"retry_count,omitempty" json:"retry_count,omitempty"`
}

type Workflow struct {
	Name        string         `yaml:"name" json:"name"`
	Version     string         `yaml:"version" json:"version"`
	Description string         `yaml:"description,omitempty" json:"description,omitempty"`
	Steps       []WorkflowStep `yaml:"steps" json:"steps"`
}

func LoadWorkflow(content []byte) (*Workflow, error) {
	var w Workflow
	if err := yaml.Unmarshal(content, &w); err != nil {
		return nil, fmt.Errorf("failed to parse workflow YAML: %w", err)
	}
	// Note: Validation logic can be added here using gojsonschema (similar to skill validation)
	return &w, nil
}

func (w *Workflow) ToJSON() ([]byte, error) {
	return json.Marshal(w)
}
