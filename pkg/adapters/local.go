// SkillPM - Local LLM Adapter (Phase 3)
// Author: Bogdan Ticu
// License: MIT
//
// Adapter for locally hosted LLMs via Ollama, LocalAI, or any
// OpenAI-compatible API endpoint. Uses the /v1/chat/completions
// endpoint format.

package adapters

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
)

type LocalLLMAdapter struct {
	Endpoint string // e.g., http://localhost:11434/v1
	Model    string // e.g., llama3, mistral, codellama
}

func NewLocalLLMAdapter() *LocalLLMAdapter {
	endpoint := os.Getenv("LOCAL_LLM_ENDPOINT")
	if endpoint == "" {
		endpoint = "http://localhost:11434/v1"
	}
	model := os.Getenv("LOCAL_LLM_MODEL")
	if model == "" {
		model = "llama3"
	}
	return &LocalLLMAdapter{
		Endpoint: endpoint,
		Model:    model,
	}
}

func (l *LocalLLMAdapter) Name() string {
	return "local-llm"
}

func (l *LocalLLMAdapter) MaxTokens() int {
	return 8192
}

func (l *LocalLLMAdapter) SupportsVision() bool {
	// Some local models (llava, etc.) support vision
	return false
}

func (l *LocalLLMAdapter) SupportsTools() bool {
	return false
}

func (l *LocalLLMAdapter) Completion(prompt string) (string, error) {
	return l.CompletionWithSystem("You are a helpful assistant.", prompt)
}

func (l *LocalLLMAdapter) CompletionWithSystem(system, prompt string) (string, error) {
	if l.Endpoint == "" {
		return "", fmt.Errorf("LOCAL_LLM_ENDPOINT not set")
	}

	messages := []map[string]interface{}{}
	if system != "" {
		messages = append(messages, map[string]interface{}{
			"role": "system", "content": system,
		})
	}
	messages = append(messages, map[string]interface{}{
		"role": "user", "content": prompt,
	})

	body := map[string]interface{}{
		"model":    l.Model,
		"messages": messages,
	}

	jsonBody, _ := json.Marshal(body)
	url := fmt.Sprintf("%s/chat/completions", l.Endpoint)

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", fmt.Errorf("local LLM request failed: %w (is the server running at %s?)", err, l.Endpoint)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("local LLM error (HTTP %d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	choices, ok := result["choices"].([]interface{})
	if !ok || len(choices) == 0 {
		return "", fmt.Errorf("no response from local LLM")
	}

	choice, _ := choices[0].(map[string]interface{})
	message, _ := choice["message"].(map[string]interface{})
	text, _ := message["content"].(string)

	return text, nil
}

func (l *LocalLLMAdapter) Vision(prompt string, imagePath string) (string, error) {
	return "", fmt.Errorf("local LLM adapter does not support vision. Use a vision-capable model")
}

func (l *LocalLLMAdapter) StreamCompletion(prompt string, callback func(token string)) error {
	result, err := l.Completion(prompt)
	if err != nil {
		return err
	}
	callback(result)
	return nil
}

func (l *LocalLLMAdapter) ToolUse(prompt string, tools []ToolDefinition) (*ToolResponse, error) {
	return nil, fmt.Errorf("local LLM adapter does not support tool use")
}
