// SkillPM - OpenAI/GPT-4 Adapter (Phase 3)
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

type OpenAIAdapter struct {
	APIKey string
	Model  string
}

func NewOpenAIAdapter() *OpenAIAdapter {
	model := os.Getenv("OPENAI_MODEL")
	if model == "" {
		model = "gpt-4o"
	}
	return &OpenAIAdapter{
		APIKey: os.Getenv("OPENAI_API_KEY"),
		Model:  model,
	}
}

func (o *OpenAIAdapter) Name() string {
	return "gpt-4"
}

func (o *OpenAIAdapter) MaxTokens() int {
	return 128000
}

func (o *OpenAIAdapter) SupportsVision() bool {
	return true
}

func (o *OpenAIAdapter) SupportsTools() bool {
	return true
}

func (o *OpenAIAdapter) Completion(prompt string) (string, error) {
	return o.CompletionWithSystem("You are a helpful assistant.", prompt)
}

func (o *OpenAIAdapter) CompletionWithSystem(system, prompt string) (string, error) {
	if o.APIKey == "" {
		return "", fmt.Errorf("OPENAI_API_KEY not set")
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
		"model":    o.Model,
		"messages": messages,
	}

	jsonBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", o.APIKey))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("OpenAI API request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("OpenAI API error (HTTP %d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	choices, ok := result["choices"].([]interface{})
	if !ok || len(choices) == 0 {
		return "", fmt.Errorf("no choices in OpenAI response")
	}

	choice, _ := choices[0].(map[string]interface{})
	message, _ := choice["message"].(map[string]interface{})
	text, _ := message["content"].(string)

	return text, nil
}

func (o *OpenAIAdapter) Vision(prompt string, imagePath string) (string, error) {
	if o.APIKey == "" {
		return "", fmt.Errorf("OPENAI_API_KEY not set")
	}

	imageData, err := os.ReadFile(imagePath)
	if err != nil {
		return "", fmt.Errorf("failed to read image: %w", err)
	}

	encoded := base64.StdEncoding.EncodeToString(imageData)

	body := map[string]interface{}{
		"model": o.Model,
		"messages": []map[string]interface{}{
			{
				"role": "user",
				"content": []map[string]interface{}{
					{
						"type": "image_url",
						"image_url": map[string]interface{}{
							"url": fmt.Sprintf("data:image/png;base64,%s", encoded),
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
	req, _ := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", o.APIKey))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("OpenAI Vision error: %s", string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	choices, ok := result["choices"].([]interface{})
	if !ok || len(choices) == 0 {
		return "", fmt.Errorf("no choices")
	}

	choice, _ := choices[0].(map[string]interface{})
	message, _ := choice["message"].(map[string]interface{})
	text, _ := message["content"].(string)
	return text, nil
}

func (o *OpenAIAdapter) StreamCompletion(prompt string, callback func(token string)) error {
	result, err := o.Completion(prompt)
	if err != nil {
		return err
	}
	callback(result)
	return nil
}

func (o *OpenAIAdapter) ToolUse(prompt string, tools []ToolDefinition) (*ToolResponse, error) {
	if o.APIKey == "" {
		return nil, fmt.Errorf("OPENAI_API_KEY not set")
	}

	openaiTools := make([]map[string]interface{}, len(tools))
	for i, t := range tools {
		properties := make(map[string]interface{})
		for pName, pDesc := range t.Parameters {
			properties[pName] = map[string]interface{}{
				"type":        "string",
				"description": pDesc,
			}
		}

		openaiTools[i] = map[string]interface{}{
			"type": "function",
			"function": map[string]interface{}{
				"name":        t.Name,
				"description": t.Description,
				"parameters": map[string]interface{}{
					"type":       "object",
					"properties": properties,
				},
			},
		}
	}

	body := map[string]interface{}{
		"model": o.Model,
		"tools": openaiTools,
		"messages": []map[string]interface{}{
			{"role": "user", "content": prompt},
		},
	}

	jsonBody, _ := json.Marshal(body)
	req, _ := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", o.APIKey))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("OpenAI error: %s", string(respBody))
	}

	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	toolResp := &ToolResponse{}

	choices, ok := result["choices"].([]interface{})
	if !ok || len(choices) == 0 {
		return toolResp, nil
	}

	choice, _ := choices[0].(map[string]interface{})
	message, _ := choice["message"].(map[string]interface{})

	if content, ok := message["content"].(string); ok {
		toolResp.Text = content
	}

	if toolCalls, ok := message["tool_calls"].([]interface{}); ok {
		for _, tc := range toolCalls {
			tcMap, _ := tc.(map[string]interface{})
			fn, _ := tcMap["function"].(map[string]interface{})
			name, _ := fn["name"].(string)
			argsStr, _ := fn["arguments"].(string)

			args := make(map[string]string)
			var argsMap map[string]interface{}
			if json.Unmarshal([]byte(argsStr), &argsMap) == nil {
				for k, v := range argsMap {
					args[k] = fmt.Sprintf("%v", v)
				}
			}

			toolResp.ToolCalls = append(toolResp.ToolCalls, ToolCall{
				Name:      name,
				Arguments: args,
			})
		}
	}

	return toolResp, nil
}
