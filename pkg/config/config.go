package config

import (
	"os"
	"path/filepath"
)

func GetSkillsDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	dir := filepath.Join(home, ".skillpm", "skills")
	err = os.MkdirAll(dir, 0755)
	return dir, err
}

func GetConfigDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	dir := filepath.Join(home, ".skillpm")
	err = os.MkdirAll(dir, 0755)
	return dir, err
}
