// SkillPM - Registry API Client
// Author: Bogdan Ticu
// License: MIT
//
// HTTP client for the SkillPM registry API. Used by the CLI
// to interact with the registry for search, install, publish,
// reviews, and analytics.

package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"

	"github.com/skillpm/skillpm/pkg/manifest"
)

type Client struct {
	BaseURL string
	APIKey  string
}

func NewClient(baseURL string) *Client {
	return &Client{BaseURL: baseURL}
}

func NewAuthenticatedClient(baseURL, apiKey string) *Client {
	return &Client{BaseURL: baseURL, APIKey: apiKey}
}

// --- Data Types ---

type RegistrySkill struct {
	ID             int      `json:"id"`
	Name           string   `json:"name"`
	Version        string   `json:"version"`
	AuthorUsername string   `json:"author_username"`
	Description    string   `json:"description"`
	License        string   `json:"license"`
	RepositoryURL  string   `json:"repository_url"`
	HomepageURL    string   `json:"homepage_url"`
	EntryPoint     string   `json:"entry_point"`
	Language       string   `json:"language"`
	DownloadCount  int      `json:"download_count"`
	AvgRating      float64  `json:"avg_rating"`
	ReviewCount    int      `json:"review_count"`
	Deprecated     bool     `json:"deprecated"`
	Metadata       Metadata `json:"metadata"`
}

type Metadata struct {
	Tags         []string                `json:"tags"`
	Language     string                  `json:"language"`
	TargetLLMs   []string                `json:"target_llms"`
	Capabilities manifest.Capabilities   `json:"capabilities"`
	Dependencies manifest.Dependencies   `json:"dependencies"`
}

type SkillListResponse struct {
	Skills  []RegistrySkill `json:"skills"`
	Total   int             `json:"total"`
	Page    int             `json:"page"`
	PerPage int             `json:"per_page"`
}

type ExecutionReport struct {
	SkillName    string `json:"skill_name"`
	Version      string `json:"version,omitempty"`
	Status       string `json:"status"`
	DurationMs   int    `json:"duration_ms"`
	ErrorMessage string `json:"error_message,omitempty"`
	LLMUsed      string `json:"llm_used,omitempty"`
}

type InstallReport struct {
	SkillName string `json:"skill_name"`
	Version   string `json:"version,omitempty"`
	Action    string `json:"action"` // install, uninstall, update
}

type RegisterRequest struct {
	Username string `json:"username"`
	Email    string `json:"email,omitempty"`
}

type RegisterResponse struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	APIKey   string `json:"api_key"`
}

type ReviewRequest struct {
	Rating int    `json:"rating"`
	Title  string `json:"title,omitempty"`
	Body   string `json:"body,omitempty"`
}

type SkillPublishRequest struct {
	Name           string                 `json:"name"`
	Version        string                 `json:"version"`
	Description    string                 `json:"description"`
	License        string                 `json:"license"`
	RepositoryURL  string                 `json:"repository_url"`
	EntryPoint     string                 `json:"entry_point,omitempty"`
	Language       string                 `json:"language,omitempty"`
	AuthorUsername string                 `json:"author_username"`
	Signature      string                 `json:"signature,omitempty"`
	Metadata       map[string]interface{} `json:"metadata"`
}

// --- HTTP helpers ---

func (c *Client) doRequest(method, path string, body interface{}) (*http.Response, error) {
	fullURL := fmt.Sprintf("%s%s", c.BaseURL, path)

	var reqBody io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reqBody = bytes.NewBuffer(data)
	}

	req, err := http.NewRequest(method, fullURL, reqBody)
	if err != nil {
		return nil, err
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.APIKey != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.APIKey))
	}
	req.Header.Set("User-Agent", "skillpm-cli/1.0")

	return http.DefaultClient.Do(req)
}

func (c *Client) doJSON(method, path string, body interface{}, result interface{}) error {
	resp, err := c.doRequest(method, path, body)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("registry error (HTTP %d): %s", resp.StatusCode, string(bodyBytes))
	}

	if result != nil {
		return json.NewDecoder(resp.Body).Decode(result)
	}
	return nil
}

// --- Public API ---

func (c *Client) Register(username, email string) (*RegisterResponse, error) {
	var result RegisterResponse
	err := c.doJSON("POST", "/api/v1/authors/register", RegisterRequest{
		Username: username,
		Email:    email,
	}, &result)
	return &result, err
}

func (c *Client) Search(query string) ([]RegistrySkill, error) {
	params := url.Values{}
	params.Add("q", query)
	var results []RegistrySkill
	err := c.doJSON("GET", fmt.Sprintf("/api/v1/search?%s", params.Encode()), nil, &results)
	return results, err
}

func (c *Client) SearchWithFilters(query, tag, language, sort string) ([]RegistrySkill, error) {
	params := url.Values{}
	if query != "" {
		params.Add("q", query)
	}
	if tag != "" {
		params.Add("tag", tag)
	}
	if language != "" {
		params.Add("language", language)
	}
	if sort != "" {
		params.Add("sort", sort)
	}
	var results []RegistrySkill
	err := c.doJSON("GET", fmt.Sprintf("/api/v1/search?%s", params.Encode()), nil, &results)
	return results, err
}

func (c *Client) GetSkill(name string) (*RegistrySkill, error) {
	var skill RegistrySkill
	err := c.doJSON("GET", fmt.Sprintf("/api/v1/skills/%s", name), nil, &skill)
	return &skill, err
}

func (c *Client) ListSkills() (*SkillListResponse, error) {
	var result SkillListResponse
	err := c.doJSON("GET", "/api/v1/skills/", nil, &result)
	return &result, err
}

func (c *Client) PublishSkill(req SkillPublishRequest) (*RegistrySkill, error) {
	var result RegistrySkill
	err := c.doJSON("POST", "/api/v1/skills/", req, &result)
	return &result, err
}

func (c *Client) ReportExecution(report ExecutionReport) error {
	return c.doJSON("POST", "/api/v1/analytics/execution", report, nil)
}

func (c *Client) ReportInstall(report InstallReport) error {
	return c.doJSON("POST", "/api/v1/analytics/install", report, nil)
}

func (c *Client) CreateReview(skillName string, review ReviewRequest) error {
	return c.doJSON("POST", fmt.Sprintf("/api/v1/skills/%s/reviews", skillName), review, nil)
}

func (c *Client) GetSkillAnalytics(skillName string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.doJSON("GET", fmt.Sprintf("/api/v1/analytics/skill/%s", skillName), nil, &result)
	return result, err
}

func (c *Client) Autocomplete(prefix string) ([]map[string]string, error) {
	params := url.Values{}
	params.Add("q", prefix)
	var result []map[string]string
	err := c.doJSON("GET", fmt.Sprintf("/api/v1/search/autocomplete?%s", params.Encode()), nil, &result)
	return result, err
}
