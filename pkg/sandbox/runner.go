// SkillPM - Hardened Docker Sandbox Runner
// Author: Bogdan Ticu
// License: MIT
//
// Runs skills inside Docker containers with security hardening:
// - seccomp profiles to restrict syscalls
// - Resource limits (CPU, memory, PIDs)
// - Read-only root filesystem
// - No new privileges
// - Network isolation by default
// - Audit logging of all execution events

package sandbox

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/skillpm/skillpm/pkg/manifest"
)

// SecurityProfile defines the container security settings.
type SecurityProfile struct {
	MemoryLimit   string // e.g. "256m"
	CPUQuota      int    // microseconds per 100ms period, 50000 = 50% of one core
	PidsLimit     int
	ReadOnlyRoot  bool
	NoNewPrivs    bool
	SeccompPath   string // path to seccomp JSON profile
	TimeoutSec    int
	DropAllCaps   bool
}

// DefaultSecurityProfile returns a sensible default for skill execution.
func DefaultSecurityProfile() SecurityProfile {
	return SecurityProfile{
		MemoryLimit:  "256m",
		CPUQuota:     50000,
		PidsLimit:    64,
		ReadOnlyRoot: true,
		NoNewPrivs:   true,
		TimeoutSec:   120,
		DropAllCaps:  true,
	}
}

// AuditEntry represents one sandbox execution event for logging.
type AuditEntry struct {
	Timestamp   string `json:"timestamp"`
	SkillName   string `json:"skill_name"`
	SkillDir    string `json:"skill_dir"`
	Image       string `json:"image"`
	ExitCode    int    `json:"exit_code"`
	DurationMs  int64  `json:"duration_ms"`
	NetworkMode string `json:"network_mode"`
	Error       string `json:"error,omitempty"`
}

type Runner struct {
	Manifest *manifest.Manifest
	SkillDir string
	Profile  SecurityProfile
}

func NewRunner(m *manifest.Manifest, skillDir string) *Runner {
	return &Runner{
		Manifest: m,
		SkillDir: skillDir,
		Profile:  DefaultSecurityProfile(),
	}
}

func NewRunnerWithProfile(m *manifest.Manifest, skillDir string, profile SecurityProfile) *Runner {
	return &Runner{
		Manifest: m,
		SkillDir: skillDir,
		Profile:  profile,
	}
}

func (r *Runner) Run(args []string) error {
	startTime := time.Now()

	// Determine base image
	image := "python:3.11-slim"
	if r.Manifest.Language == "javascript" || r.Manifest.Language == "typescript" {
		image = "node:18-alpine"
	} else if r.Manifest.Language == "go" {
		image = "golang:1.22-alpine"
	}

	dockerArgs := []string{"run", "--rm", "-i"}

	// --- Security hardening ---

	// Resource limits
	dockerArgs = append(dockerArgs,
		"--memory", r.Profile.MemoryLimit,
		"--cpu-quota", fmt.Sprintf("%d", r.Profile.CPUQuota),
		"--pids-limit", fmt.Sprintf("%d", r.Profile.PidsLimit),
	)

	// Read-only root filesystem
	if r.Profile.ReadOnlyRoot {
		dockerArgs = append(dockerArgs, "--read-only")
		// Provide a writable /tmp for languages that need it
		dockerArgs = append(dockerArgs, "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m")
	}

	// No new privileges
	if r.Profile.NoNewPrivs {
		dockerArgs = append(dockerArgs, "--security-opt", "no-new-privileges:true")
	}

	// Drop all capabilities
	if r.Profile.DropAllCaps {
		dockerArgs = append(dockerArgs, "--cap-drop", "ALL")
	}

	// Seccomp profile
	if r.Profile.SeccompPath != "" {
		if _, err := os.Stat(r.Profile.SeccompPath); err == nil {
			dockerArgs = append(dockerArgs, "--security-opt", fmt.Sprintf("seccomp=%s", r.Profile.SeccompPath))
		}
	}

	// User namespacing: run as non-root inside container
	dockerArgs = append(dockerArgs, "--user", "1000:1000")

	// --- LLM environment injection ---
	llm := os.Getenv("SKILLPM_LLM")
	if llm == "" {
		llm = "claude"
	}
	dockerArgs = append(dockerArgs, "-e", fmt.Sprintf("SKILLPM_LLM=%s", llm))

	switch llm {
	case "claude":
		if key := os.Getenv("CLAUDE_API_KEY"); key != "" {
			dockerArgs = append(dockerArgs, "-e", fmt.Sprintf("CLAUDE_API_KEY=%s", key))
		}
	case "gpt-4", "openai":
		if key := os.Getenv("OPENAI_API_KEY"); key != "" {
			dockerArgs = append(dockerArgs, "-e", fmt.Sprintf("OPENAI_API_KEY=%s", key))
		}
	case "gemini":
		if key := os.Getenv("GEMINI_API_KEY"); key != "" {
			dockerArgs = append(dockerArgs, "-e", fmt.Sprintf("GEMINI_API_KEY=%s", key))
		}
	case "local-llm":
		if endpoint := os.Getenv("LOCAL_LLM_ENDPOINT"); endpoint != "" {
			dockerArgs = append(dockerArgs, "-e", fmt.Sprintf("LOCAL_LLM_ENDPOINT=%s", endpoint))
			dockerArgs = append(dockerArgs, "--add-host=host.docker.internal:host-gateway")
		}
		if model := os.Getenv("LOCAL_LLM_MODEL"); model != "" {
			dockerArgs = append(dockerArgs, "-e", fmt.Sprintf("LOCAL_LLM_MODEL=%s", model))
		}
	}

	// --- Volume mounts ---

	// Mount skill directory as read-only
	dockerArgs = append(dockerArgs, "-v", fmt.Sprintf("%s:/app:ro", r.SkillDir))
	dockerArgs = append(dockerArgs, "-w", "/app")

	// Capability-based file mounts
	if r.Manifest.Capabilities != nil {
		if r.Manifest.Capabilities.FileRead != nil {
			for _, path := range r.Manifest.Capabilities.FileRead.Paths {
				cleanPath := strings.TrimSuffix(path, "/*")
				if cleanPath != "" {
					dockerArgs = append(dockerArgs, "-v", fmt.Sprintf("%s:%s:ro", cleanPath, cleanPath))
				}
			}
		}
		if r.Manifest.Capabilities.FileWrite != nil {
			for _, path := range r.Manifest.Capabilities.FileWrite.Paths {
				cleanPath := strings.TrimSuffix(path, "/*")
				if cleanPath != "" {
					dockerArgs = append(dockerArgs, "-v", fmt.Sprintf("%s:%s:rw", cleanPath, cleanPath))
				}
			}
		}
	}

	// --- Network policy ---
	networkMode := "none"
	if r.Manifest.Capabilities != nil && len(r.Manifest.Capabilities.Network) > 0 {
		networkMode = "bridge"
	}
	dockerArgs = append(dockerArgs, "--network", networkMode)

	// --- Entry point ---
	switch r.Manifest.Language {
	case "python":
		dockerArgs = append(dockerArgs, image, "python", r.Manifest.EntryPoint)
	case "javascript", "typescript":
		dockerArgs = append(dockerArgs, image, "node", r.Manifest.EntryPoint)
	default:
		dockerArgs = append(dockerArgs, image, "sh", "-c", r.Manifest.EntryPoint)
	}

	// Append user arguments
	dockerArgs = append(dockerArgs, args...)

	fmt.Printf("[sandbox] Executing: docker %s\n", strings.Join(dockerArgs, " "))

	cmd := exec.Command("docker", dockerArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	runErr := cmd.Run()
	duration := time.Since(startTime)

	// --- Audit logging ---
	exitCode := 0
	errMsg := ""
	if runErr != nil {
		exitCode = 1
		errMsg = runErr.Error()
		if exitErr, ok := runErr.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		}
	}

	entry := AuditEntry{
		Timestamp:   startTime.UTC().Format(time.RFC3339),
		SkillName:   r.Manifest.Name,
		SkillDir:    r.SkillDir,
		Image:       image,
		ExitCode:    exitCode,
		DurationMs:  duration.Milliseconds(),
		NetworkMode: networkMode,
		Error:       errMsg,
	}
	writeAuditLog(entry)

	return runErr
}

// writeAuditLog appends an audit entry to the SkillPM audit log file.
func writeAuditLog(entry AuditEntry) {
	home, err := os.UserHomeDir()
	if err != nil {
		return
	}
	logDir := filepath.Join(home, ".skillpm", "logs")
	os.MkdirAll(logDir, 0755)

	logFile := filepath.Join(logDir, "sandbox_audit.jsonl")
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	data, err := json.Marshal(entry)
	if err != nil {
		return
	}
	f.Write(data)
	f.Write([]byte("\n"))
}
