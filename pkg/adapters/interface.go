// SkillPM - LLM Adapter Interface (Phase 3)
// Author: Bogdan Ticu
// License: MIT
//
// Defines the standard interface that all LLM adapters must implement.
// This allows skills to be written once and run against any supported
// LLM backend: Claude, GPT-4, Gemini, or local models via Ollama/LocalAI.

package adapters

import "fmt"

// LLMAdapter is the core interface for model-specific implementations.
type LLMAdapter interface {
	// Name returns the identifier of the adapter (e.g., "claude", "gpt-4")
	Name() string

	// Completion sends a text prompt and returns the response.
	Completion(prompt string) (string, error)

	// CompletionWithSystem sends a prompt with a system message.
	CompletionWithSystem(system, prompt string) (string, error)

	// Vision handles multimodal requests with images.
	Vision(prompt string, imagePath string) (string, error)

	// StreamCompletion sends a prompt and streams tokens via callback.
	StreamCompletion(prompt string, callback func(token string)) error

	// ToolUse sends a prompt with tool definitions and returns
	// the model's tool call decisions.
	ToolUse(prompt string, tools []ToolDefinition) (*ToolResponse, error)

	// MaxTokens returns the maximum context window size.
	MaxTokens() int

	// SupportsVision returns whether this adapter supports image inputs.
	SupportsVision() bool

	// SupportsTools returns whether this adapter supports tool/function calling.
	SupportsTools() bool
}

// ToolDefinition describes a tool that the LLM can call.
type ToolDefinition struct {
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Parameters  map[string]string `json:"parameters"` // param_name -> description
}

// ToolCall represents a single tool invocation by the LLM.
type ToolCall struct {
	Name       string            `json:"name"`
	Arguments  map[string]string `json:"arguments"`
}

// ToolResponse wraps the LLM's response which may include tool calls.
type ToolResponse struct {
	Text      string     `json:"text,omitempty"`
	ToolCalls []ToolCall `json:"tool_calls,omitempty"`
}

// GetAdapter returns the appropriate adapter for the given LLM name.
func GetAdapter(name string) (LLMAdapter, error) {
	switch name {
	case "claude":
		return NewClaudeAdapter(), nil
	case "gpt-4", "openai":
		return NewOpenAIAdapter(), nil
	case "gemini":
		return NewGeminiAdapter(), nil
	case "local-llm", "local":
		return NewLocalLLMAdapter(), nil
	default:
		return nil, fmt.Errorf("unknown LLM adapter: %s", name)
	}
}
