package provider

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// APIClient is the HTTP client for rcloud API
type APIClient struct {
	Endpoint          string
	Token             string
	SSHUser           string
	SSHPublicKeyFile  string
	HTTPClient        *http.Client
}

// VM represents a virtual machine
type VM struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	State     string `json:"state"`
	VCPUs     int64  `json:"vcpus"`
	MemoryMB  int64  `json:"memory_mb"`
	IPAddress string `json:"ip_address,omitempty"`
}

// CreateVMRequest is the request to create a VM
type CreateVMRequest struct {
	Name          string  `json:"name"`
	VCPUs         int64   `json:"vcpus"`
	MemoryMB      int64   `json:"memory_mb"`
	BaseImage     string  `json:"base_image"`
	RootDiskGB    int64   `json:"root_disk_gb"`
	SSHUser       *string `json:"ssh_user,omitempty"`
	SSHPublicKey  *string `json:"ssh_public_key,omitempty"`
}

// CreateVMResponse is the response from creating a VM
type CreateVMResponse struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	State string `json:"state"`
}

// NewHTTPClient creates a new HTTP client with timeout
func (c *APIClient) newHTTPClient() *http.Client {
	if c.HTTPClient != nil {
		return c.HTTPClient
	}
	return &http.Client{
		Timeout: 30 * time.Second,
	}
}

// CreateVM creates a new VM
func (c *APIClient) CreateVM(req *CreateVMRequest) (*CreateVMResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequest("POST", c.Endpoint+"/api/v1/vms", bytes.NewBuffer(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	if c.Token != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.Token)
	}

	client := c.newHTTPClient()
	resp, err := client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var createResp CreateVMResponse
	if err := json.NewDecoder(resp.Body).Decode(&createResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &createResp, nil
}

// GetVM retrieves a VM by ID
func (c *APIClient) GetVM(id string) (*VM, error) {
	httpReq, err := http.NewRequest("GET", c.Endpoint+"/api/v1/vms/"+id, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	if c.Token != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.Token)
	}

	client := c.newHTTPClient()
	resp, err := client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("VM not found")
	}

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var vm VM
	if err := json.NewDecoder(resp.Body).Decode(&vm); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &vm, nil
}

// DeleteVM deletes a VM
func (c *APIClient) DeleteVM(id string) error {
	httpReq, err := http.NewRequest("DELETE", c.Endpoint+"/api/v1/vms/"+id, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	if c.Token != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.Token)
	}

	client := c.newHTTPClient()
	resp, err := client.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}

// StartVM starts a VM
func (c *APIClient) StartVM(id string) error {
	httpReq, err := http.NewRequest("POST", c.Endpoint+"/api/v1/vms/"+id+"/start", nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	if c.Token != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.Token)
	}

	client := c.newHTTPClient()
	resp, err := client.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}

// StopVM stops a VM
func (c *APIClient) StopVM(id string) error {
	httpReq, err := http.NewRequest("POST", c.Endpoint+"/api/v1/vms/"+id+"/stop", nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	if c.Token != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.Token)
	}

	client := c.newHTTPClient()
	resp, err := client.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}
