package provider

import (
	"context"
	"fmt"
	"os"
	"time"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/int64planmodifier"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/planmodifier"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/stringplanmodifier"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-log/tflog"
)

// Ensure provider defined types fully satisfy framework interfaces.
var _ resource.Resource = &VMResource{}
var _ resource.ResourceWithImportState = &VMResource{}

func NewVMResource() resource.Resource {
	return &VMResource{}
}

// VMResource defines the resource implementation.
type VMResource struct {
	client *APIClient
}

// VMResourceModel describes the resource data model.
type VMResourceModel struct {
	ID               types.String `tfsdk:"id"`
	Name             types.String `tfsdk:"name"`
	VCPUs            types.Int64  `tfsdk:"vcpus"`
	MemoryGB         types.Int64  `tfsdk:"memory_gb"`
	BaseImage        types.String `tfsdk:"base_image"`
	RootDiskGB       types.Int64  `tfsdk:"root_disk_gb"`
	SSHUser          types.String `tfsdk:"ssh_user"`
	SSHPublicKeyFile types.String `tfsdk:"ssh_public_key_file"`
	State            types.String `tfsdk:"state"`
	IPAddress        types.String `tfsdk:"ip_address"`
}

func (r *VMResource) Metadata(ctx context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_vm"
}

func (r *VMResource) Schema(ctx context.Context, req resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		// This description is used by the documentation generator and the language server.
		MarkdownDescription: "rcloud VM resource",

		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "VM identifier (UUID)",
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.UseStateForUnknown(),
				},
			},
			"name": schema.StringAttribute{
				MarkdownDescription: "VM name",
				Required:            true,
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.RequiresReplace(),
				},
			},
			"vcpus": schema.Int64Attribute{
				MarkdownDescription: "Number of virtual CPUs",
				Required:            true,
				PlanModifiers: []planmodifier.Int64{
					int64planmodifier.RequiresReplace(),
				},
			},
			"memory_gb": schema.Int64Attribute{
				MarkdownDescription: "Memory in GB",
				Required:            true,
				PlanModifiers: []planmodifier.Int64{
					int64planmodifier.RequiresReplace(),
				},
			},
			"base_image": schema.StringAttribute{
				MarkdownDescription: "Base image filename from guestfs",
				Required:            true,
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.RequiresReplace(),
				},
			},
			"root_disk_gb": schema.Int64Attribute{
				MarkdownDescription: "Root disk size in GB",
				Required:            true,
				PlanModifiers: []planmodifier.Int64{
					int64planmodifier.RequiresReplace(),
				},
			},
			"ssh_user": schema.StringAttribute{
				MarkdownDescription: "SSH username to create (defaults to provider configuration)",
				Optional:            true,
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.RequiresReplace(),
				},
			},
			"ssh_public_key_file": schema.StringAttribute{
				MarkdownDescription: "Path to SSH public key file (defaults to provider configuration)",
				Optional:            true,
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.RequiresReplace(),
				},
			},
			"state": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "VM state",
			},
			"ip_address": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "VM IP address (available when VM is running with qemu-guest-agent)",
			},
		},
	}
}

func (r *VMResource) Configure(ctx context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	// Prevent panic if the provider has not been configured.
	if req.ProviderData == nil {
		return
	}

	client, ok := req.ProviderData.(*APIClient)

	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Resource Configure Type",
			fmt.Sprintf("Expected *APIClient, got: %T. Please report this issue to the provider developers.", req.ProviderData),
		)

		return
	}

	r.client = client
}

func (r *VMResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var data VMResourceModel

	// Read Terraform plan data into the model
	resp.Diagnostics.Append(req.Plan.Get(ctx, &data)...)

	if resp.Diagnostics.HasError() {
		return
	}

	// Determine SSH user: resource > provider > none
	var sshUser *string
	if !data.SSHUser.IsNull() {
		val := data.SSHUser.ValueString()
		sshUser = &val
	} else if r.client.SSHUser != "" {
		sshUser = &r.client.SSHUser
	}

	// Determine SSH public key file: resource > provider > none
	sshPublicKeyFile := ""
	if !data.SSHPublicKeyFile.IsNull() {
		sshPublicKeyFile = data.SSHPublicKeyFile.ValueString()
	} else if r.client.SSHPublicKeyFile != "" {
		sshPublicKeyFile = r.client.SSHPublicKeyFile
	}

	// Read SSH public key content if file path is provided
	var sshPublicKey *string
	if sshPublicKeyFile != "" {
		keyContent, err := os.ReadFile(sshPublicKeyFile)
		if err != nil {
			resp.Diagnostics.AddError(
				"SSH Key Read Error",
				fmt.Sprintf("Unable to read SSH public key from %s: %s", sshPublicKeyFile, err),
			)
			return
		}
		keyStr := string(keyContent)
		sshPublicKey = &keyStr
		tflog.Debug(ctx, "Read SSH public key", map[string]any{"file": sshPublicKeyFile, "length": len(keyStr)})
	}

	// Create API request
	createReq := &CreateVMRequest{
		Name:         data.Name.ValueString(),
		VCPUs:        data.VCPUs.ValueInt64(),
		MemoryMB:     data.MemoryGB.ValueInt64() * 1024, // Convert GB to MB
		BaseImage:    data.BaseImage.ValueString(),
		RootDiskGB:   data.RootDiskGB.ValueInt64(),
		SSHUser:      sshUser,
		SSHPublicKey: sshPublicKey,
	}

	tflog.Info(ctx, "Creating VM", map[string]any{"name": createReq.Name, "ssh_user": sshUser != nil, "ssh_key": sshPublicKey != nil})

	// Call API
	createResp, err := r.client.CreateVM(createReq)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", fmt.Sprintf("Unable to create VM, got error: %s", err))
		return
	}

	// Set the ID from create response
	data.ID = types.StringValue(createResp.ID)

	tflog.Trace(ctx, "Created VM", map[string]any{"id": createResp.ID})

	// Wait for VM to boot and get IP address (with timeout)
	// VMs need time to boot, start networking, and acquire DHCP lease
	// We MUST wait for IP address before returning - bringup process depends on it
	maxRetries := 300  // 5 minutes total (300 seconds)
	retryDelay := 1 * time.Second

	var vm *VM
	var ipAcquired bool
	for i := 0; i < maxRetries; i++ {
		vm, err = r.client.GetVM(data.ID.ValueString())
		if err != nil {
			resp.Diagnostics.AddError("Client Error", fmt.Sprintf("Unable to read VM after creation, got error: %s", err))
			return
		}

		// If we have an IP address, we're done
		if vm.IPAddress != "" {
			tflog.Info(ctx, "VM acquired IP address", map[string]any{"ip": vm.IPAddress, "attempts": i + 1, "elapsed_seconds": i + 1})
			ipAcquired = true
			break
		}

		// Log progress every 30 seconds
		if i > 0 && i % 30 == 0 {
			tflog.Info(ctx, "Still waiting for VM IP address", map[string]any{"elapsed_seconds": i, "max_seconds": maxRetries})
		}

		// Wait before retrying
		if i < maxRetries - 1 {
			tflog.Debug(ctx, "Waiting for VM IP address", map[string]any{"attempt": i + 1, "max": maxRetries})
			time.Sleep(retryDelay)
		}
	}

	// CRITICAL: VM creation must not succeed without an IP address
	// The bringup process needs the IP address to configure SSH access
	if !ipAcquired {
		resp.Diagnostics.AddError(
			"VM Boot Timeout",
			fmt.Sprintf("VM %s was created and started but did not acquire an IP address within %d seconds. "+
				"This typically indicates a networking issue with the base image or libvirt network configuration. "+
				"Check that the VM has networking configured and that the libvirt default network is active.",
				data.Name.ValueString(), maxRetries),
		)
		// Attempt to clean up the VM since it's not usable without an IP
		tflog.Warn(ctx, "Attempting to delete VM due to timeout", map[string]any{"id": data.ID.ValueString()})
		if cleanupErr := r.client.DeleteVM(data.ID.ValueString()); cleanupErr != nil {
			tflog.Error(ctx, "Failed to clean up VM after timeout", map[string]any{"error": cleanupErr.Error()})
		}
		return
	}

	// Populate all computed fields from the final API response
	data.State = types.StringValue(vm.State)
	data.IPAddress = types.StringValue(vm.IPAddress)

	// Save data into Terraform state
	resp.Diagnostics.Append(resp.State.Set(ctx, &data)...)
}

func (r *VMResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var data VMResourceModel

	// Read Terraform prior state data into the model
	resp.Diagnostics.Append(req.State.Get(ctx, &data)...)

	if resp.Diagnostics.HasError() {
		return
	}

	// Get VM from API
	vm, err := r.client.GetVM(data.ID.ValueString())
	if err != nil {
		resp.Diagnostics.AddError("Client Error", fmt.Sprintf("Unable to read VM, got error: %s", err))
		return
	}

	// Update state
	data.State = types.StringValue(vm.State)

	// Update IP address if available
	if vm.IPAddress != "" {
		data.IPAddress = types.StringValue(vm.IPAddress)
	} else {
		data.IPAddress = types.StringNull()
	}

	// Save updated data into Terraform state
	resp.Diagnostics.Append(resp.State.Set(ctx, &data)...)
}

func (r *VMResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var data VMResourceModel

	// Read Terraform plan data into the model
	resp.Diagnostics.Append(req.Plan.Get(ctx, &data)...)

	if resp.Diagnostics.HasError() {
		return
	}

	// Most VM attributes require replacement, so update is a no-op
	// In the future, could support live updates like memory/vcpu hotplug

	// Save updated data into Terraform state
	resp.Diagnostics.Append(resp.State.Set(ctx, &data)...)
}

func (r *VMResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var data VMResourceModel

	// Read Terraform prior state data into the model
	resp.Diagnostics.Append(req.State.Get(ctx, &data)...)

	if resp.Diagnostics.HasError() {
		return
	}

	tflog.Info(ctx, "Deleting VM", map[string]any{"id": data.ID.ValueString()})

	// Delete VM via API
	err := r.client.DeleteVM(data.ID.ValueString())
	if err != nil {
		resp.Diagnostics.AddError("Client Error", fmt.Sprintf("Unable to delete VM, got error: %s", err))
		return
	}

	tflog.Trace(ctx, "Deleted VM", map[string]any{"id": data.ID.ValueString()})
}

func (r *VMResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("id"), req, resp)
}
