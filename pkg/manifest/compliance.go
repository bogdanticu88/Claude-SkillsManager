package manifest

import (
	"fmt"
	"regexp"
)

var (
	// Simple regex patterns for common secrets
	openaiKeyPattern = regexp.MustCompile(`sk-[a-zA-Z0-9]{48}`)
	awsKeyPattern    = regexp.MustCompile(`AKIA[0-9A-Z]{16}`)
)

// CheckCompliance scans the manifest and skill files for common security violations
func CheckCompliance(content []byte) error {
	// Scan for OpenAI keys
	if openaiKeyPattern.Match(content) {
		return fmt.Errorf("security violation: found potential OpenAI API key in manifest")
	}

	// Scan for AWS keys
	if awsKeyPattern.Match(content) {
		return fmt.Errorf("security violation: found potential AWS access key in manifest")
	}

	return nil
}
