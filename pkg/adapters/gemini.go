// SkillPM - Gemini Adapter (Phase 3)
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

type GeminiAdapter struct {
	APIKey string
	Model  string
}

func NewGeminiAdapter() *GeminiAdapter {
	model := os.Getenv("GEMINI_MODEL")
	if model == "" {
		model = "gemini-2.0-flash"
	}
	return &GeminiAdapter{
		APIKey: os.Getenv("GEMINI_API_KEY"),
		Model:  model,
	}
}

func (g *GeminiAdapter) Name() string {
	return "gemini"
}

func (g *GeminiAdapter) MaxTokens() int {
	return 1000000
}

func (g *GeminiAdapter) SupportsVision() bool {
	return true
}

func (g *GeminiAdapter) SupportsTools() bool {
	return true
}

func (g *GeminiAdapter) Completion(prompt string) (string, error) {
	return g.CompletionWithSystem("", prompt)
}

func (g *GeminiAdapter) CompletionWithSystem(system, prompt string) (string, error) {
	if g.APIKey == "" {
		return "", fmt.Errorf("GEMINI_API_KEY not set")
	}

	contents := []map[string]interface{}{
		{
			"role": "user",
			"parts": []map[string]interface{}{
				{"text": prompt},
			},
		},
	}

	body := map[string]interface{}{
		"contents": contents,
	}

	if system != "" {
		body["systemInstruction"] = map[string]interface{}{
			"parts": []map[string]interface{}{
				{"text": system},
			},
		}
	}

	url := fmt.Sprintf(
		"https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s",
		g.Model, g.APIKey,
	)

	jsonBody, _ := json.Marshal(body)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", fmt.Errorf("Gemini API request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("Gemini API error (HTTP %d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	candidates, ok := result["candidates"].([]interface{})
	if !ok || len(candidates) == 0 {
		return "", fmt.Errorf("no candidates in Gemini response")
	}

	candidate, _ := candidates[0].(map[string]interface{})
	content, _ := candidate["content"].(map[string]interface{})
	parts, _ := content["parts"].([]interface{})

	if len(parts) == 0 {
		return "", fmt.Errorf("no parts in Gemini response")
	}

	firstPart, _ := parts[0].(map[string]interface{})
	text, _ := firstPart["text"].(string)
	return text, nil
}

func (g *GeminiAdapter) Vision(prompt string, imagePath string) (string, error) {
	if g.APIKey == "" {
		return "", fmt.Errorf("GEMINI_API_KEY not set")
	}

	imageData, err := os.ReadFile(imagePath)
	if err != nil {
		return "", fmt.Errorf("failed to read image: %w", err)
	}

	encoded := base64.StdEncoding.EncodeToString(imageData)
	mimeType := "image/png"

	body := map[string]interface{}{
		"contents": []map[string]interface{}{
			{
				"parts": []map[string]interface{}{
					{
						"inline_data": map[string]interface{}{
							"mime_type": mimeType,
							"data":     encoded,
						},
					},
					{"text": prompt},
				},
			},
		},
	}

	url := fmt.Sprintf(
		"https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s",
		g.Model, g.APIKey,
	)

	jsonBody, _ := json.Marshal(body)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("Gemini Vision error: %s", string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	candidates, ok := result["candidates"].([]interface{})
	if !ok || len(candidates) == 0 {
		return "", fmt.Errorf("no response from Gemini Vision")
	}

	candidate, _ := candidates[0].(map[string]interface{})
	content, _ := candidate["content"].(map[string]interface{})
	parts, _ := content["parts"].([]interface{})

	if len(parts) == 0 {
		return "", fmt.Errorf("empty response")
	}

	firstPart, _ := parts[0].(map[string]interface{})
	text, _ := firstPart["text"].(string)
	return text, nil
}

func (g *GeminiAdapter) StreamCompletion(prompt string, callback func(token string)) error {
	result, err := g.Completion(prompt)
	if err != nil {
		return err
	}
	callback(result)
	return nil
}

func (g *GeminiAdapter) ToolUse(prompt string, tools []ToolDefinition) (*ToolResponse, error) {
	// Gemini tool use via function declarations
	if g.APIKey == "" {
		return nil, fmt.Errorf("GEMINI_API_KEY not set")
	}

	funcDecls := make([]map[string]interface{}, len(tools))
	for i, t := range tools {
		properties := make(map[string]interface{})
		for pName, pDesc := range t.Parameters {
			properties[pName] = map[string]interface{}{
				"type":        "string",
				"description": pDesc,
			}
		}

		funcDecls[i] = map[string]interface{}{
			"name":        t.Name,
			"description": t.Description,
			"parameters": map[string]interface{}{
				"type":       "object",
				"properties": properties,
			},
		}
	}

	body := map[string]interface{}{
		"contents": []map[string]interface{}{
			{
				"parts": []map[string]interface{}{
					{"text": prompt},
				},
			},
		},
		"tools": []map[string]interface{}{
			{"function_declarations": funcDecls},
		},
	}

	url := fmt.Sprintf(
		"https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s",
		g.Model, g.APIKey,
	)

	jsonBody, _ := json.Marshal(body)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("Gemini error: %s", string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	toolResp := &ToolResponse{}

	candidates, ok := result["candidates"].([]interface{})
	if !ok || len(candidates) == 0 {
		return toolResp, nil
	}

	candidate, _ := candidates[0].(map[string]interface{})
	content, _ := candidate["content"].(map[string]interface{})
	parts, _ := content["parts"].([]interface{})

	for _, part := range parts {
		p, ok := part.(map[string]interface{})
		if !ok {
			continue
		}

		if text, ok := p["text"].(string); ok {
			toolResp.Text = text
		}

		if fc, ok := p["functionCall"].(map[string]interface{}); ok {
			name, _ := fc["name"].(string)
			argsRaw, _ := fc["args"].(map[string]interface{})
			args := make(map[string]string)
			for k, v := range argsRaw {
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
