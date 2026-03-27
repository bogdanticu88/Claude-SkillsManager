// SkillPM - Workflow Executor (Phase 1.5)
// Author: Bogdan Ticu
// License: MIT
//
// The workflow executor handles multi-skill composition. It parses
// workflow YAML files that define step sequences, supports parallel
// execution, conditional steps, error handling (retry, skip, fail),
// and data passing between steps via outputs.

package sandbox

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/skillpm/skillpm/pkg/config"
	"github.com/skillpm/skillpm/pkg/manifest"
)

// WorkflowExecutor manages the execution of a multi-step skill workflow.
type WorkflowExecutor struct {
	Workflow *manifest.Workflow
	Results  map[string]*StepResult
	mu       sync.Mutex
	Profile  SecurityProfile
}

// StepResult holds the outcome of a single workflow step.
type StepResult struct {
	Status     string `json:"status"`      // SUCCESS, FAILURE, SKIPPED
	Output     string `json:"output"`
	Error      string `json:"error,omitempty"`
	DurationMs int64  `json:"duration_ms"`
	Retries    int    `json:"retries"`
}

// WorkflowReport is the final summary of a workflow execution.
type WorkflowReport struct {
	WorkflowName string                 `json:"workflow_name"`
	Version      string                 `json:"version"`
	Status       string                 `json:"status"` // COMPLETED, FAILED
	TotalSteps   int                    `json:"total_steps"`
	StepResults  map[string]*StepResult `json:"step_results"`
	TotalTimeMs  int64                  `json:"total_time_ms"`
	StartedAt    string                 `json:"started_at"`
	FinishedAt   string                 `json:"finished_at"`
}

func NewWorkflowExecutor(w *manifest.Workflow) *WorkflowExecutor {
	return &WorkflowExecutor{
		Workflow: w,
		Results:  make(map[string]*StepResult),
		Profile:  DefaultSecurityProfile(),
	}
}

func NewWorkflowExecutorWithProfile(w *manifest.Workflow, profile SecurityProfile) *WorkflowExecutor {
	return &WorkflowExecutor{
		Workflow: w,
		Results:  make(map[string]*StepResult),
		Profile:  profile,
	}
}

// Execute runs all workflow steps respecting order, parallelism, and conditions.
func (e *WorkflowExecutor) Execute() error {
	startTime := time.Now()
	fmt.Printf("[workflow] Starting: %s v%s (%d steps)\n", e.Workflow.Name, e.Workflow.Version, len(e.Workflow.Steps))

	skillsDir, err := config.GetSkillsDir()
	if err != nil {
		return fmt.Errorf("failed to get skills directory: %w", err)
	}

	overallStatus := "COMPLETED"

	for i := 0; i < len(e.Workflow.Steps); i++ {
		step := e.Workflow.Steps[i]

		// 1. Check conditional execution
		if step.If != "" {
			e.mu.Lock()
			prevResult, exists := e.Results[step.If]
			e.mu.Unlock()

			if !exists || prevResult.Status != "SUCCESS" {
				fmt.Printf("\n[step %d/%d] Skipping '%s' (condition '%s' not met)\n",
					i+1, len(e.Workflow.Steps), step.Name, step.If)
				e.mu.Lock()
				e.Results[step.Name] = &StepResult{Status: "SKIPPED"}
				e.mu.Unlock()
				continue
			}
		}

		// 2. Handle parallel block
		if step.Parallel {
			j := i
			for j < len(e.Workflow.Steps) && e.Workflow.Steps[j].Parallel {
				j++
			}

			parallelSteps := e.Workflow.Steps[i:j]
			fmt.Printf("\n[parallel] Running %d steps concurrently...\n", len(parallelSteps))

			var wg sync.WaitGroup
			var parallelErrors []error
			var errMu sync.Mutex

			for _, ps := range parallelSteps {
				wg.Add(1)
				go func(s manifest.WorkflowStep) {
					defer wg.Done()
					result := e.runStepWithRetry(s, skillsDir)
					e.mu.Lock()
					e.Results[s.Name] = result
					e.mu.Unlock()

					if result.Status == "FAILURE" {
						errMu.Lock()
						parallelErrors = append(parallelErrors, fmt.Errorf("step '%s' failed: %s", s.Name, result.Error))
						errMu.Unlock()
					}
				}(ps)
			}
			wg.Wait()

			if len(parallelErrors) > 0 {
				overallStatus = "FAILED"
				// Check if all parallel steps have skip policy
				allSkippable := true
				for _, ps := range parallelSteps {
					if ps.OnError == nil || ps.OnError.Action != "skip" {
						allSkippable = false
						break
					}
				}
				if !allSkippable {
					e.writeReport(startTime, overallStatus)
					return parallelErrors[0]
				}
			}

			i = j - 1
			continue
		}

		// 3. Sequential step with error handling
		result := e.runStepWithRetry(step, skillsDir)
		e.mu.Lock()
		e.Results[step.Name] = result
		e.mu.Unlock()

		if result.Status == "FAILURE" {
			if step.OnError != nil && step.OnError.Action == "skip" {
				fmt.Printf("[step] '%s' failed, policy: skip. Continuing.\n", step.Name)
				continue
			}
			overallStatus = "FAILED"
			e.writeReport(startTime, overallStatus)
			return fmt.Errorf("workflow failed at step '%s': %s", step.Name, result.Error)
		}
	}

	e.writeReport(startTime, overallStatus)
	fmt.Printf("\n[workflow] '%s' completed successfully.\n", e.Workflow.Name)
	return nil
}

// runStepWithRetry executes a step, applying retry policy if configured.
func (e *WorkflowExecutor) runStepWithRetry(step manifest.WorkflowStep, skillsDir string) *StepResult {
	maxAttempts := 1
	if step.OnError != nil && step.OnError.Action == "retry" && step.OnError.RetryCount > 0 {
		maxAttempts = step.OnError.RetryCount + 1
	}

	var result *StepResult
	for attempt := 0; attempt < maxAttempts; attempt++ {
		if attempt > 0 {
			fmt.Printf("[retry] Step '%s' attempt %d/%d\n", step.Name, attempt+1, maxAttempts)
		}

		result = e.runStep(step, skillsDir)
		if result.Status == "SUCCESS" {
			result.Retries = attempt
			return result
		}
	}

	result.Retries = maxAttempts - 1
	return result
}

// runStep executes a single workflow step inside the sandbox.
func (e *WorkflowExecutor) runStep(step manifest.WorkflowStep, skillsDir string) *StepResult {
	startTime := time.Now()
	fmt.Printf("\n[step] Executing: %s (skill: %s)\n", step.Name, step.Skill)

	skillPath := filepath.Join(skillsDir, step.Skill)
	manifestPath := filepath.Join(skillPath, "skill.yaml")
	content, err := os.ReadFile(manifestPath)
	if err != nil {
		return &StepResult{
			Status:     "FAILURE",
			Error:      fmt.Sprintf("skill '%s' not found at %s", step.Skill, skillPath),
			DurationMs: time.Since(startTime).Milliseconds(),
		}
	}

	m, err := manifest.Load(content)
	if err != nil {
		return &StepResult{
			Status:     "FAILURE",
			Error:      fmt.Sprintf("invalid manifest for '%s': %v", step.Skill, err),
			DurationMs: time.Since(startTime).Milliseconds(),
		}
	}

	// Build arguments
	args := []string{}
	if step.Input != "" {
		e.mu.Lock()
		if prevResult, ok := e.Results[step.Input]; ok && prevResult.Output != "" {
			args = append(args, prevResult.Output)
		} else {
			args = append(args, step.Input)
		}
		e.mu.Unlock()
	}

	runner := NewRunnerWithProfile(m, skillPath, e.Profile)
	err = runner.Run(args)
	duration := time.Since(startTime)

	if err != nil {
		return &StepResult{
			Status:     "FAILURE",
			Error:      err.Error(),
			DurationMs: duration.Milliseconds(),
		}
	}

	return &StepResult{
		Status:     "SUCCESS",
		Output:     step.Output,
		DurationMs: duration.Milliseconds(),
	}
}

// writeReport writes the workflow execution report to disk.
func (e *WorkflowExecutor) writeReport(startTime time.Time, status string) {
	report := WorkflowReport{
		WorkflowName: e.Workflow.Name,
		Version:      e.Workflow.Version,
		Status:       status,
		TotalSteps:   len(e.Workflow.Steps),
		StepResults:  e.Results,
		TotalTimeMs:  time.Since(startTime).Milliseconds(),
		StartedAt:    startTime.UTC().Format(time.RFC3339),
		FinishedAt:   time.Now().UTC().Format(time.RFC3339),
	}

	home, err := os.UserHomeDir()
	if err != nil {
		return
	}

	logDir := filepath.Join(home, ".skillpm", "logs")
	os.MkdirAll(logDir, 0755)

	logFile := filepath.Join(logDir, "workflow_reports.jsonl")
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	data, err := json.Marshal(report)
	if err != nil {
		return
	}
	f.Write(data)
	f.Write([]byte("\n"))
}
