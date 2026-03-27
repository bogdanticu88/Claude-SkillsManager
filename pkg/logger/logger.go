package logger

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/skillpm/skillpm/pkg/config"
)

type AuditLog struct {
	Timestamp time.Time `json:"timestamp"`
	Action    string    `json:"action"`
	SkillName string    `json:"skill_name"`
	Details   string    `json:"details"`
}

func LogAction(skillName, action, details string) error {
	logDir, err := config.GetConfigDir()
	if err != nil {
		return err
	}
	logsPath := filepath.Join(logDir, "logs")
	os.MkdirAll(logsPath, 0755)

	logFile := filepath.Join(logsPath, fmt.Sprintf("%s.log", skillName))
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	entry := AuditLog{
		Timestamp: time.Now(),
		Action:    action,
		SkillName: skillName,
		Details:   details,
	}

	b, err := json.Marshal(entry)
	if err != nil {
		return err
	}

	_, err = f.WriteString(string(b) + "\n")
	return err
}
