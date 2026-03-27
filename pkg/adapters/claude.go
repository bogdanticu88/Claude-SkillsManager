// SkillPM - Claude Adapter (Phase 3)
// Author: Bogdan Ticu
// License: MIT

package adapters

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
)

type ClaudeAdapter struct {
	APIKey string
	Model  string
}

func NewClaudeAdapter() *ClaudeAdapter {
	model := os.Getenv("CLAUDE_MODEL")
	if model == "" {
		model = "claude-sonnet-4-20250514"
	}
	return &ClaudeAdapter{
		APIKey: os.Getenv("CLAUDE_API_KEY"),
		Model:  model,
	}
}

func (c *ClaudeAdapter) Name() string {
	return "claude"
}

func (c *ClaudeAdapter) MaxTokens() int {
	return 200000
}

func (c *ClaudeAdapter) SupportsVision() bool {
	return true
}

func (c *ClaudeAdapter) SupportsTools() bool {
	return true
}

func (c *ClaudeAdapter) Completion(prompt string) (string, error) {
	return c.CompletionWithSystem("You are a helpful assistant.", prompt)
}

func (c *ClaudeAdapter) CompletionWithSystem(system, prompt string) (string, error) {
	if c.APIKey == "" {
		return "", fmt.Errorf("CLAUDE_API_KEY not set")
	}

	body := map[string]interface{}{
		"model":      c.Model,
		"max_tokens": 4096,
		"system":     system,
		"messages": []map[string]interface{}{
			{"role": "user", "content": prompt},
		},
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return "", err
	}

	req, err := http.NewRequest("POST", "https://api.anthropic.com/v1/messages", bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", c.APIKey)
	req.Header.Set("anthropic-version", "2023-06-01")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("Claude API request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("Claude API error (HTTP %d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return "", err
	}

	content, ok := result["content"].([]interface{})
	if !ok || len(content) == 0 {
		return "", fmt.Errorf("unexpected response format from Claude API")
	}

	firstBlock, ok := content[0].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("unexpected content block format")
	}

	text, _ := firstBlock["text"].(string)
	return text, nil
}

func (c *ClaudeAdapter) Vision(prompt string, imagePath string) (string, error) {
	if c.APIKey == "" {
		return "", fmt.Errorf("CLAUDE_API_KEY not set")
	}

	imageData, err := os.ReadFile(imagePath)
	if err != nil {
		return "", fmt.Errorf("failed to read image: %w", err)
	}

	encoded := base64.StdEncoding.EncodeToString(imageData)
	mediaType := "image/png"
	if len(imagePath) > 4 {
		ext := imagePath[len(imagePath)-4:]
		if ext == ".jpg" || ext == "jpeg" {
			mediaType = "image/jpeg"
		} else if ext == ".gif" {
			mediaType = "image/gif"
		} else if ext == "webp" {
			mediaType = "image/webp"
		}
	}

	body := map[string]interface{}{
		"model":      c.Model,
		"max_tokens": 4096,
		"messages": []map[string]interface{}{
			{
				"role": "user",
				"content": []map[string]interface{}{
					{
						"type": "image",
						"source": map[string]interface{}{
							"type":       "base64",
							"media_type": mediaType,
							"data":       encoded,
						},
					},
					{
						"type": "text",
						"text": prompt,
					},
				},
			},
		},
	}

	jsonBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", "https://api.anthropic.com/v1/messages", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", c.APIKey)
	req.Header.Set("anthropic-version", "2023-06-01")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("Claude Vision API error: %s", string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	content, ok := result["content"].([]interface{})
	if !ok || len(content) == 0 {
		return "", fmt.Errorf("unexpected response")
	}

	firstBlock, _ := content[0].(map[string]interface{})
	text, _ := firstBlock["text"].(string)
	return text, nil
}

func (c *ClaudeAdapter) StreamCompletion(prompt string, callback func(token string)) error {
	// Streaming implementation uses SSE from Claude API
	// For now, fall back to non-streaming
	result, err := c.Completion(prompt)
	if err != nil {
		return err
	}
	callback(result)
	return nil
}

func (c *ClaudeAdapter) ToolUse(prompt string, tools []ToolDefinition) (*ToolResponse, error) {
	if c.APIKey == "" {
		return nil, fmt.Errorf("CLAUDE_API_KEY not set")
	}

	// Convert tool definitions to Claude format
	claudeTools := make([]map[string]interface{}, len(tools))
	for i, t := range tools {
		properties := make(map[string]interface{})
		for pName, pDesc := range t.Parameters {
			properties[pName] = map[string]interface{}{
				"type":        "string",
				"description": pDesc,
			}
		}

		claudeTools[i] = map[string]interface{}{
			"name":        t.Name,
			"description": t.Description,
			"input_schema": map[string]interface{}{
				"type":       "object",
				"properties": properties,
			},
		}
	}

	body := map[string]interface{}{
		"model":      c.Model,
		"max_tokens": 4096,
		"tools":      claudeTools,
		"messages": []map[string]interface{}{
			{"role": "user", "content": prompt},
		},
	}

	jsonBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", "https://api.anthropic.com/v1/messages", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", c.APIKey)
	req.Header.Set("anthropic-version", "2023-06-01")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("Claude API error: %s", string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	toolResp := &ToolResponse{}

	content, ok := result["content"].([]interface{})
	if !ok {
		return toolResp, nil
	}

	for _, block := range content {
		b, ok := block.(map[string]interface{})
		if !ok {
			continue
		}

		blockType, _ := b["type"].(string)
		if blockType == "text" {
			toolResp.Text, _ = b["text"].(string)
		} else if blockType == "tool_use" {
			name, _ := b["name"].(string)
			input, _ := b["input"].(map[string]interface{})
			args := make(map[string]string)
			for k, v := range input {
				args[k] = fmt.Sprintf("%v", v)
			}
			toolResp.ToolCalls = append(toolResp.ToolCalls, ToolCall{
				Name:      name,
				Arguments: args,
			})
		}
	}

	return toolResp, nil
}
