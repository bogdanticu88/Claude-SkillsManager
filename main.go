// SkillPM - CLI Package Manager for LLM Skills
// Author: Bogdan Ticu
// License: MIT
//
// The main command-line interface for managing LLM skills.
// Supports search, install, run, publish, review, and workflow commands.

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/skillpm/skillpm/pkg/adapters"
	"github.com/skillpm/skillpm/pkg/api"
	"github.com/skillpm/skillpm/pkg/config"
	"github.com/skillpm/skillpm/pkg/generator"
	"github.com/skillpm/skillpm/pkg/gpg"
	"github.com/skillpm/skillpm/pkg/logger"
	"github.com/skillpm/skillpm/pkg/manifest"
	"github.com/skillpm/skillpm/pkg/sandbox"
	"github.com/urfave/cli/v2"
)

const version = "1.0.0"

func getRegistryClient() *api.Client {
	registryURL := os.Getenv("SKILLPM_REGISTRY")
	if registryURL == "" {
		registryURL = "http://localhost:8000"
	}
	apiKey := os.Getenv("SKILLPM_API_KEY")
	if apiKey != "" {
		return api.NewAuthenticatedClient(registryURL, apiKey)
	}
	return api.NewClient(registryURL)
}

func installSkill(client *api.Client, target string, installed map[string]bool) error {
	if installed[target] {
		return nil
	}

	skillsDir, err := config.GetSkillsDir()
	if err != nil {
		return err
	}

	var repoURL string
	var skillName string
	var skillVersion string

	if filepath.IsAbs(target) || (len(target) > 4 && target[:4] == "http") {
		repoURL = target
		skillName = filepath.Base(repoURL)
		if strings.HasSuffix(skillName, ".git") {
			skillName = strings.TrimSuffix(skillName, ".git")
		}
	} else {
		skill, err := client.GetSkill(target)
		if err != nil {
			return fmt.Errorf("failed to find skill %s in registry: %w", target, err)
		}
		repoURL = skill.RepositoryURL
		skillName = skill.Name
		skillVersion = skill.Version
	}

	targetPath := filepath.Join(skillsDir, skillName)
	if _, err := os.Stat(targetPath); err == nil {
		fmt.Printf("  %s is already installed.\n", skillName)
		installed[skillName] = true
		return resolveDependencies(client, targetPath, installed)
	}

	fmt.Printf("  Installing %s from %s...\n", skillName, repoURL)
	cmd := exec.Command("git", "clone", "--depth", "1", repoURL, targetPath)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to clone %s: %w", repoURL, err)
	}

	installed[skillName] = true

	// Report install to registry (best effort)
	_ = client.ReportInstall(api.InstallReport{
		SkillName: skillName,
		Version:   skillVersion,
		Action:    "install",
	})

	return resolveDependencies(client, targetPath, installed)
}

func resolveDependencies(client *api.Client, skillPath string, installed map[string]bool) error {
	manifestPath := filepath.Join(skillPath, "skill.yaml")
	content, err := os.ReadFile(manifestPath)
	if err != nil {
		return nil
	}

	m, err := manifest.Load(content)
	if err != nil {
		return err
	}

	if m.Dependencies != nil && len(m.Dependencies.Skills) > 0 {
		fmt.Printf("  Resolving dependencies for %s...\n", m.Name)
		for _, depName := range m.Dependencies.Skills {
			if err := installSkill(client, depName, installed); err != nil {
				return fmt.Errorf("failed to install dependency %s: %w", depName, err)
			}
		}
	}
	return nil
}

func main() {
	registryClient := getRegistryClient()

	app := &cli.App{
		Name:    "skillpm",
		Usage:   "Package manager for LLM skills",
		Version: version,
		Commands: []*cli.Command{

			// --- Search ---
			{
				Name:    "search",
				Aliases: []string{"s"},
				Usage:   "Search registry for skills",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "tag", Usage: "Filter by tag"},
					&cli.StringFlag{Name: "language", Usage: "Filter by language (python, javascript)"},
					&cli.StringFlag{Name: "sort", Usage: "Sort by: relevance, downloads, rating, name, newest", Value: "relevance"},
				},
				Action: func(c *cli.Context) error {
					query := ""
					if c.NArg() > 0 {
						query = c.Args().Get(0)
					}

					results, err := registryClient.SearchWithFilters(
						query,
						c.String("tag"),
						c.String("language"),
						c.String("sort"),
					)
					if err != nil {
						return err
					}

					if len(results) == 0 {
						fmt.Printf("No results found for '%s'\n", query)
						return nil
					}

					fmt.Printf("Found %d skills:\n\n", len(results))
					for _, r := range results {
						stars := ""
						if r.AvgRating > 0 {
							stars = fmt.Sprintf(" [%.1f/5]", r.AvgRating)
						}
						deprecated := ""
						if r.Deprecated {
							deprecated = " [DEPRECATED]"
						}
						fmt.Printf("  %s (%s) by %s%s%s\n", r.Name, r.Version, r.AuthorUsername, stars, deprecated)
						if r.Description != "" {
							fmt.Printf("    %s\n", r.Description)
						}
						fmt.Printf("    Downloads: %d | Reviews: %d\n\n", r.DownloadCount, r.ReviewCount)
					}
					return nil
				},
			},

			// --- Install ---
			{
				Name:    "install",
				Aliases: []string{"i"},
				Usage:   "Install a skill and its dependencies",
				Flags: []cli.Flag{
					&cli.BoolFlag{Name: "verify", Usage: "Verify GPG signature before installing"},
				},
				Action: func(c *cli.Context) error {
					if c.NArg() == 0 {
						return fmt.Errorf("please provide a skill name or repository URL")
					}
					target := c.Args().Get(0)
					installed := make(map[string]bool)

					fmt.Println("Installing skill...")
					if err := installSkill(registryClient, target, installed); err != nil {
						return err
					}

					// Optional GPG verification
					if c.Bool("verify") {
						skillsDir, _ := config.GetSkillsDir()
						skillPath := filepath.Join(skillsDir, target)
						sigPath := filepath.Join(skillPath, "skill.yaml.asc")
						manifestPath := filepath.Join(skillPath, "skill.yaml")

						if _, err := os.Stat(sigPath); err == nil {
							data, _ := os.ReadFile(manifestPath)
							sig, _ := os.ReadFile(sigPath)
							if err := gpg.VerifyWithLocalKey(data, sig); err != nil {
								fmt.Printf("  WARNING: Signature verification failed: %v\n", err)
							} else {
								fmt.Println("  Signature verified successfully.")
							}
						} else {
							fmt.Println("  No signature file found. Skipping verification.")
						}
					}

					fmt.Println("Installation complete.")
					return nil
				},
			},

			// --- Uninstall ---
			{
				Name:    "uninstall",
				Aliases: []string{"rm"},
				Usage:   "Remove an installed skill",
				Action: func(c *cli.Context) error {
					if c.NArg() == 0 {
						return fmt.Errorf("please provide a skill name")
					}
					name := c.Args().Get(0)
					skillsDir, err := config.GetSkillsDir()
					if err != nil {
						return err
					}

					skillPath := filepath.Join(skillsDir, name)
					if _, err := os.Stat(skillPath); os.IsNotExist(err) {
						return fmt.Errorf("skill %s is not installed", name)
					}

					if err := os.RemoveAll(skillPath); err != nil {
						return fmt.Errorf("failed to remove skill: %w", err)
					}

					_ = registryClient.ReportInstall(api.InstallReport{
						SkillName: name,
						Action:    "uninstall",
					})

					fmt.Printf("Removed skill %s.\n", name)
					return nil
				},
			},

			// --- Run ---
			{
				Name:  "run",
				Usage: "Run a skill in a sandboxed container",
				Flags: []cli.Flag{
					&cli.StringFlag{
						Name:  "llm",
						Usage: "Override the LLM backend (claude, gpt-4, gemini, local-llm)",
						Value: "claude",
					},
					&cli.StringFlag{
						Name:  "local-endpoint",
						Usage: "Endpoint for local LLM",
						Value: "http://host.docker.internal:11434/v1",
					},
					&cli.StringFlag{
						Name:  "local-model",
						Usage: "Model name for local LLM",
						Value: "llama3",
					},
					&cli.StringFlag{
						Name:  "memory",
						Usage: "Container memory limit",
						Value: "256m",
					},
					&cli.IntFlag{
						Name:  "timeout",
						Usage: "Execution timeout in seconds",
						Value: 120,
					},
					&cli.BoolFlag{
						Name:  "telemetry",
						Usage: "Report anonymized execution data to registry",
					},
				},
				Action: func(c *cli.Context) error {
					if c.NArg() == 0 {
						return fmt.Errorf("please provide a skill name")
					}
					name := c.Args().Get(0)

					os.Setenv("SKILLPM_LLM", c.String("llm"))
					if c.String("llm") == "local-llm" {
						os.Setenv("LOCAL_LLM_ENDPOINT", c.String("local-endpoint"))
						os.Setenv("LOCAL_LLM_MODEL", c.String("local-model"))
					}

					skillsDir, err := config.GetSkillsDir()
					if err != nil {
						return err
					}

					skillPath := filepath.Join(skillsDir, name)
					manifestPath := filepath.Join(skillPath, "skill.yaml")
					content, err := os.ReadFile(manifestPath)
					if err != nil {
						return fmt.Errorf("skill %s not found locally. Install it first with: skillpm install %s", name, name)
					}

					m, err := manifest.Load(content)
					if err != nil {
						return err
					}

					logger.LogAction(name, "EXECUTE", "Starting sandboxed execution")

					profile := sandbox.DefaultSecurityProfile()
					profile.MemoryLimit = c.String("memory")
					profile.TimeoutSec = c.Int("timeout")

					startTime := time.Now()
					runner := sandbox.NewRunnerWithProfile(m, skillPath, profile)
					runErr := runner.Run(c.Args().Slice()[1:])
					duration := time.Since(startTime)

					status := "SUCCESS"
					errMsg := ""
					if runErr != nil {
						status = "FAILURE"
						errMsg = runErr.Error()
						logger.LogAction(name, "FAILURE", errMsg)
					} else {
						logger.LogAction(name, "SUCCESS", "Execution completed")
					}

					if c.Bool("telemetry") {
						_ = registryClient.ReportExecution(api.ExecutionReport{
							SkillName:    name,
							Version:      m.Version,
							Status:       status,
							DurationMs:   int(duration.Milliseconds()),
							ErrorMessage: errMsg,
							LLMUsed:      c.String("llm"),
						})
					}

					return runErr
				},
			},

			// --- Publish ---
			{
				Name:  "publish",
				Usage: "Publish a skill to the registry",
				Flags: []cli.Flag{
					&cli.BoolFlag{Name: "sign", Usage: "Sign the manifest with your GPG key"},
				},
				Action: func(c *cli.Context) error {
					path := "."
					if c.NArg() > 0 {
						path = c.Args().Get(0)
					}

					manifestPath := filepath.Join(path, "skill.yaml")
					content, err := os.ReadFile(manifestPath)
					if err != nil {
						return fmt.Errorf("failed to read skill.yaml: %w", err)
					}

					if err := manifest.Validate(content); err != nil {
						return fmt.Errorf("invalid manifest: %w", err)
					}

					if err := manifest.CheckCompliance(content); err != nil {
						return fmt.Errorf("compliance check failed: %w", err)
					}

					m, err := manifest.Load(content)
					if err != nil {
						return err
					}

					var signature string
					if c.Bool("sign") {
						sig, err := gpg.Sign(content)
						if err != nil {
							return fmt.Errorf("failed to sign manifest: %w", err)
						}
						signature = string(sig)

						// Also write the .asc file locally
						sigPath := filepath.Join(path, "skill.yaml.asc")
						os.WriteFile(sigPath, sig, 0644)
						fmt.Printf("Signed manifest written to %s\n", sigPath)
					}

					pubReq := api.SkillPublishRequest{
						Name:           m.Name,
						Version:        m.Version,
						Description:    m.Description,
						License:        m.License,
						RepositoryURL:  m.Repository,
						EntryPoint:     m.EntryPoint,
						Language:        m.Language,
						AuthorUsername:  m.Author,
						Signature:       signature,
						Metadata: map[string]interface{}{
							"tags":        m.Tags,
							"language":    m.Language,
							"target_llms": m.TargetLLMs,
							"capabilities": map[string]interface{}{},
							"dependencies": map[string]interface{}{},
						},
					}

					result, err := registryClient.PublishSkill(pubReq)
					if err != nil {
						return fmt.Errorf("failed to publish: %w", err)
					}

					fmt.Printf("Published %s v%s to registry.\n", result.Name, result.Version)
					return nil
				},
			},

			// --- Create ---
			{
				Name:  "create",
				Usage: "Generate a skill package using AI from a prompt",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "output", Usage: "Output directory", Value: "."},
					&cli.StringFlag{Name: "llm", Usage: "Model for generation", Value: "claude"},
				},
				Action: func(c *cli.Context) error {
					if c.NArg() == 0 {
						return fmt.Errorf("please provide a prompt")
					}
					prompt := c.Args().Get(0)
					targetDir := c.String("output")

					var adapter adapters.LLMAdapter
					switch c.String("llm") {
					case "claude":
						adapter = &adapters.ClaudeAdapter{APIKey: os.Getenv("CLAUDE_API_KEY")}
					case "gpt-4", "openai":
						adapter = &adapters.OpenAIAdapter{APIKey: os.Getenv("OPENAI_API_KEY")}
					default:
						adapter = &adapters.ClaudeAdapter{APIKey: os.Getenv("CLAUDE_API_KEY")}
					}

					gen := generator.NewSkillGenerator(adapter)
					return gen.Generate(prompt, targetDir)
				},
			},

			// --- List ---
			{
				Name:    "list",
				Aliases: []string{"ls"},
				Usage:   "List installed skills or registry skills",
				Flags: []cli.Flag{
					&cli.BoolFlag{Name: "registry", Aliases: []string{"r"}, Usage: "List registry skills instead"},
				},
				Action: func(c *cli.Context) error {
					if c.Bool("registry") {
						result, err := registryClient.ListSkills()
						if err != nil {
							return err
						}
						fmt.Printf("Registry skills (%d total):\n\n", result.Total)
						for _, r := range result.Skills {
							fmt.Printf("  %s (%s) by %s\n", r.Name, r.Version, r.AuthorUsername)
						}
						return nil
					}

					skillsDir, err := config.GetSkillsDir()
					if err != nil {
						return err
					}

					entries, err := os.ReadDir(skillsDir)
					if err != nil {
						fmt.Println("No skills installed yet.")
						return nil
					}

					fmt.Printf("Installed skills (%s):\n\n", skillsDir)
					for _, entry := range entries {
						if entry.IsDir() {
							manifestPath := filepath.Join(skillsDir, entry.Name(), "skill.yaml")
							content, err := os.ReadFile(manifestPath)
							if err == nil {
								m, err := manifest.Load(content)
								if err == nil {
									fmt.Printf("  %s (%s) by %s\n", m.Name, m.Version, m.Author)
									continue
								}
							}
							fmt.Printf("  %s (invalid manifest)\n", entry.Name())
						}
					}
					return nil
				},
			},

			// --- Info ---
			{
				Name:  "info",
				Usage: "Show detailed information about a skill",
				Action: func(c *cli.Context) error {
					if c.NArg() == 0 {
						return fmt.Errorf("please provide a skill name")
					}
					name := c.Args().Get(0)

					skill, err := registryClient.GetSkill(name)
					if err != nil {
						return err
					}

					fmt.Printf("Name:        %s\n", skill.Name)
					fmt.Printf("Version:     %s\n", skill.Version)
					fmt.Printf("Author:      %s\n", skill.AuthorUsername)
					fmt.Printf("License:     %s\n", skill.License)
					fmt.Printf("Language:    %s\n", skill.Language)
					fmt.Printf("Downloads:   %d\n", skill.DownloadCount)
					fmt.Printf("Rating:      %.1f/5 (%d reviews)\n", skill.AvgRating, skill.ReviewCount)
					fmt.Printf("Repository:  %s\n", skill.RepositoryURL)
					if skill.Description != "" {
						fmt.Printf("\n%s\n", skill.Description)
					}
					if len(skill.Metadata.Tags) > 0 {
						fmt.Printf("\nTags: %s\n", strings.Join(skill.Metadata.Tags, ", "))
					}
					if len(skill.Metadata.TargetLLMs) > 0 {
						fmt.Printf("Target LLMs: %s\n", strings.Join(skill.Metadata.TargetLLMs, ", "))
					}
					if skill.Deprecated {
						fmt.Printf("\nWARNING: This skill is deprecated.\n")
					}
					return nil
				},
			},

			// --- Review ---
			{
				Name:  "review",
				Usage: "Leave a review for a skill",
				Flags: []cli.Flag{
					&cli.IntFlag{Name: "rating", Aliases: []string{"r"}, Usage: "Rating 1-5", Required: true},
					&cli.StringFlag{Name: "title", Aliases: []string{"t"}, Usage: "Review title"},
					&cli.StringFlag{Name: "body", Aliases: []string{"b"}, Usage: "Review body"},
				},
				Action: func(c *cli.Context) error {
					if c.NArg() == 0 {
						return fmt.Errorf("please provide a skill name")
					}
					name := c.Args().Get(0)
					rating := c.Int("rating")

					if rating < 1 || rating > 5 {
						return fmt.Errorf("rating must be between 1 and 5")
					}

					err := registryClient.CreateReview(name, api.ReviewRequest{
						Rating: rating,
						Title:  c.String("title"),
						Body:   c.String("body"),
					})
					if err != nil {
						return err
					}

					fmt.Printf("Review submitted for %s (%d/5).\n", name, rating)
					return nil
				},
			},

			// --- Stats ---
			{
				Name:  "stats",
				Usage: "Show analytics for a skill",
				Action: func(c *cli.Context) error {
					if c.NArg() == 0 {
						return fmt.Errorf("please provide a skill name")
					}
					name := c.Args().Get(0)

					analytics, err := registryClient.GetSkillAnalytics(name)
					if err != nil {
						return err
					}

					data, _ := json.MarshalIndent(analytics, "", "  ")
					fmt.Println(string(data))
					return nil
				},
			},

			// --- Auth ---
			{
				Name:  "auth",
				Usage: "Authentication and GPG key management",
				Subcommands: []*cli.Command{
					{
						Name:  "register",
						Usage: "Register a new account on the registry",
						Flags: []cli.Flag{
							&cli.StringFlag{Name: "username", Aliases: []string{"u"}, Required: true},
							&cli.StringFlag{Name: "email", Aliases: []string{"e"}},
						},
						Action: func(c *cli.Context) error {
							result, err := registryClient.Register(c.String("username"), c.String("email"))
							if err != nil {
								return err
							}
							fmt.Printf("Registered as %s\n", result.Username)
							fmt.Printf("API Key: %s\n", result.APIKey)
							fmt.Printf("\nSave this key. Set it as SKILLPM_API_KEY environment variable.\n")
							return nil
						},
					},
					{
						Name:  "gen-key",
						Usage: "Generate a new GPG key for skill signing",
						Flags: []cli.Flag{
							&cli.StringFlag{Name: "name", Usage: "Author Name", Required: true},
							&cli.StringFlag{Name: "email", Usage: "Author Email", Required: true},
						},
						Action: func(c *cli.Context) error {
							err := gpg.GenerateKey(c.String("name"), c.String("email"))
							if err != nil {
								return err
							}
							fmt.Println("GPG key generated successfully.")
							return nil
						},
					},
					{
						Name:  "export-key",
						Usage: "Export your public GPG key (for sharing or uploading to registry)",
						Action: func(c *cli.Context) error {
							key, err := gpg.ExportPublicKey()
							if err != nil {
								return err
							}
							fmt.Println(key)
							return nil
						},
					},
					{
						Name:  "fingerprint",
						Usage: "Show your GPG key fingerprint",
						Action: func(c *cli.Context) error {
							fp, err := gpg.GetFingerprint()
							if err != nil {
								return err
							}
							fmt.Printf("Fingerprint: %s\n", fp)
							return nil
						},
					},
				},
			},

			// --- Package ---
			{
				Name:  "package",
				Usage: "Validate and sign a skill for publishing",
				Action: func(c *cli.Context) error {
					path := "."
					if c.NArg() > 0 {
						path = c.Args().Get(0)
					}

					manifestPath := filepath.Join(path, "skill.yaml")
					content, err := os.ReadFile(manifestPath)
					if err != nil {
						return fmt.Errorf("failed to read manifest: %w", err)
					}

					if err := manifest.Validate(content); err != nil {
						return fmt.Errorf("invalid manifest: %w", err)
					}

					if err := manifest.CheckCompliance(content); err != nil {
						return fmt.Errorf("compliance failure: %w", err)
					}

					sig, err := gpg.Sign(content)
					if err != nil {
						return fmt.Errorf("failed to sign manifest: %w", err)
					}

					sigPath := filepath.Join(path, "skill.yaml.asc")
					err = os.WriteFile(sigPath, sig, 0644)
					if err != nil {
						return fmt.Errorf("failed to write signature: %w", err)
					}

					fmt.Printf("Skill at %s packaged and signed.\n", path)
					fmt.Printf("Signature: %s\n", sigPath)
					return nil
				},
			},

			// --- Verify ---
			{
				Name:  "verify",
				Usage: "Verify a skill's GPG signature",
				Action: func(c *cli.Context) error {
					path := "."
					if c.NArg() > 0 {
						path = c.Args().Get(0)
					}

					manifestPath := filepath.Join(path, "skill.yaml")
					sigPath := filepath.Join(path, "skill.yaml.asc")

					data, err := os.ReadFile(manifestPath)
					if err != nil {
						return fmt.Errorf("failed to read manifest: %w", err)
					}

					sig, err := os.ReadFile(sigPath)
					if err != nil {
						return fmt.Errorf("no signature file found at %s", sigPath)
					}

					if err := gpg.VerifyWithLocalKey(data, sig); err != nil {
						return fmt.Errorf("verification FAILED: %w", err)
					}

					fmt.Println("Signature verification PASSED.")
					return nil
				},
			},

			// --- Workflow ---
			{
				Name:  "workflow",
				Usage: "Manage and run skill workflows",
				Subcommands: []*cli.Command{
					{
						Name:  "run",
						Usage: "Run a workflow from a YAML file",
						Action: func(c *cli.Context) error {
							if c.NArg() == 0 {
								return fmt.Errorf("please provide a path to a workflow file")
							}
							path := c.Args().Get(0)
							content, err := os.ReadFile(path)
							if err != nil {
								return fmt.Errorf("failed to read workflow: %w", err)
							}

							w, err := manifest.LoadWorkflow(content)
							if err != nil {
								return err
							}

							executor := sandbox.NewWorkflowExecutor(w)
							return executor.Execute()
						},
					},
				},
			},

			// --- Audit ---
			{
				Name:  "audit",
				Usage: "View sandbox execution audit log",
				Flags: []cli.Flag{
					&cli.IntFlag{Name: "last", Aliases: []string{"n"}, Value: 20, Usage: "Show last N entries"},
				},
				Action: func(c *cli.Context) error {
					home, err := os.UserHomeDir()
					if err != nil {
						return err
					}
					logFile := filepath.Join(home, ".skillpm", "logs", "sandbox_audit.jsonl")
					data, err := os.ReadFile(logFile)
					if err != nil {
						fmt.Println("No audit log entries found.")
						return nil
					}

					lines := strings.Split(strings.TrimSpace(string(data)), "\n")
					limit := c.Int("last")
					start := 0
					if len(lines) > limit {
						start = len(lines) - limit
					}

					fmt.Printf("Last %d sandbox executions:\n\n", min(limit, len(lines)))
					for _, line := range lines[start:] {
						var entry sandbox.AuditEntry
						if err := json.Unmarshal([]byte(line), &entry); err != nil {
							continue
						}
						status := "OK"
						if entry.ExitCode != 0 {
							status = fmt.Sprintf("FAIL (exit %d)", entry.ExitCode)
						}
						fmt.Printf("  [%s] %s - %s (%dms) network=%s\n",
							entry.Timestamp[:19], entry.SkillName, status,
							entry.DurationMs, entry.NetworkMode)
						if entry.Error != "" {
							fmt.Printf("    Error: %s\n", entry.Error)
						}
					}
					return nil
				},
			},
		},
	}

	err := app.Run(os.Args)
	if err != nil {
		log.Fatal(err)
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
