package generator

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/skillpm/skillpm/pkg/adapters"
)

type SkillGenerator struct {
	Adapter adapters.LLMAdapter
}

func NewSkillGenerator(adapter adapters.LLMAdapter) *SkillGenerator {
	return &SkillGenerator{Adapter: adapter}
}

func (g *SkillGenerator) Generate(prompt string, targetDir string) error {
	fmt.Printf("🤖 Generating skill from prompt: '%s'...\n", prompt)

	systemPrompt := `You are a SkillPM expert. Generate a complete AI skill package based on the user's prompt.
Return the result in EXACTLY this format, separated by "---FILE: <filename>---":

---FILE: skill.yaml---
<manifest content>
---FILE: main.py---
<code content>
---FILE: test_skill.py---
<test content>

Requirements:
- skill.yaml must follow the SkillPM JSON schema.
- code must be functional and use the provided capabilities.
- include at least one test.
`

	fullPrompt := fmt.Sprintf("%s\n\nUser Request: %s", systemPrompt, prompt)
	response, err := g.Adapter.Completion(fullPrompt)
	if err != nil {
		return fmt.Errorf("LLM generation failed: %w", err)
	}

	// Basic parsing of the multi-file response
	files := strings.Split(response, "---FILE: ")
	for _, fileBlock := range files {
		if strings.TrimSpace(fileBlock) == "" {
			continue
		}
		parts := strings.SplitN(fileBlock, "---", 2)
		if len(parts) < 2 {
			continue
		}
		filename := strings.TrimSpace(parts[0])
		content := strings.TrimSpace(parts[1])

		filePath := filepath.Join(targetDir, filename)
		err := os.MkdirAll(filepath.Dir(filePath), 0755)
		if err != nil {
			return err
		}

		err = os.WriteFile(filePath, []byte(content), 0644)
		if err != nil {
			return fmt.Errorf("failed to write %s: %w", filename, err)
		}
		fmt.Printf("✅ Generated %s\n", filename)
	}

	return nil
}
