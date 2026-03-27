package manifest

type CapabilityFile struct {
	Paths []string `json:"paths" yaml:"paths"`
}

type CapabilityNetwork struct {
	Domain   string   `json:"domain" yaml:"domain"`
	Protocol []string `json:"protocol" yaml:"protocol"`
	Ports    []int    `json:"ports,omitempty" yaml:"ports,omitempty"`
}

type CapabilitySubprocess struct {
	AllowedCommands []string `json:"allowed_commands" yaml:"allowed_commands"`
}

type CapabilitySkillInvoke struct {
	Skills []string `json:"skills" yaml:"skills"`
}

type CapabilityUserData struct {
	Fields []string `json:"fields" yaml:"fields"`
}

type CapabilitySystem struct {
	EnvVars []string `json:"env_vars" yaml:"env_vars"`
}

type Capabilities struct {
	FileRead    *CapabilityFile       `json:"file_read,omitempty" yaml:"file_read,omitempty"`
	FileWrite   *CapabilityFile       `json:"file_write,omitempty" yaml:"file_write,omitempty"`
	FileDelete  *CapabilityFile       `json:"file_delete,omitempty" yaml:"file_delete,omitempty"`
	Network     []CapabilityNetwork   `json:"network,omitempty" yaml:"network,omitempty"`
	Subprocess  *CapabilitySubprocess `json:"subprocess,omitempty" yaml:"subprocess,omitempty"`
	SkillInvoke *CapabilitySkillInvoke `json:"skill_invoke,omitempty" yaml:"skill_invoke,omitempty"`
	UserData    *CapabilityUserData   `json:"user_data,omitempty" yaml:"user_data,omitempty"`
	System      *CapabilitySystem     `json:"system,omitempty" yaml:"system,omitempty"`
}

type Dependencies struct {
	Skills []string `json:"skills,omitempty" yaml:"skills,omitempty"`
	System []string `json:"system,omitempty" yaml:"system,omitempty"`
}

type Requires struct {
	MinVersion string `json:"min_version,omitempty" yaml:"min_version,omitempty"`
}

type Manifest struct {
	Name             string       `json:"name" yaml:"name"`
	Version          string       `json:"version" yaml:"version"`
	Author           string       `json:"author" yaml:"author"`
	Description      string       `json:"description" yaml:"description"`
	License          string       `json:"license" yaml:"license"`
	EntryPoint       string       `json:"entry_point" yaml:"entry_point"`
	Language         string       `json:"language" yaml:"language"`
	TargetLLMs       []string     `json:"target_llms" yaml:"target_llms"`
	Capabilities     *Capabilities `json:"capabilities,omitempty" yaml:"capabilities,omitempty"`
	Dependencies     *Dependencies `json:"dependencies,omitempty" yaml:"dependencies,omitempty"`
	Tags             []string     `json:"tags,omitempty" yaml:"tags,omitempty"`
	Repository       string       `json:"repository,omitempty" yaml:"repository,omitempty"`
	Homepage         string       `json:"homepage,omitempty" yaml:"homepage,omitempty"`
	Requires         *Requires     `json:"requires,omitempty" yaml:"requires,omitempty"`
	AuthorVerified   bool         `json:"author_verified,omitempty" yaml:"author_verified,omitempty"`
	MaintenanceStatus string       `json:"maintenance_status,omitempty" yaml:"maintenance_status,omitempty"`
}
