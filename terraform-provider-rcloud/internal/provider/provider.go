package provider

import (
	"context"
	"os"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// Ensure RcloudProvider satisfies various provider interfaces.
var _ provider.Provider = &RcloudProvider{}

// RcloudProvider defines the provider implementation.
type RcloudProvider struct {
	// version is set to the provider version on release, "dev" when the
	// provider is built and ran locally, and "test" when running acceptance
	// testing.
	version string
}

// RcloudProviderModel describes the provider data model.
type RcloudProviderModel struct {
	Endpoint          types.String `tfsdk:"endpoint"`
	Token             types.String `tfsdk:"token"`
	SSHUser           types.String `tfsdk:"ssh_user"`
	SSHPublicKeyFile  types.String `tfsdk:"ssh_public_key_file"`
}

func (p *RcloudProvider) Metadata(ctx context.Context, req provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "rcloud"
	resp.Version = p.version
}

func (p *RcloudProvider) Schema(ctx context.Context, req provider.SchemaRequest, resp *provider.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"endpoint": schema.StringAttribute{
				MarkdownDescription: "rcloud API endpoint URL",
				Optional:            true,
			},
			"token": schema.StringAttribute{
				MarkdownDescription: "API token for authentication (optional for MVP)",
				Optional:            true,
				Sensitive:           true,
			},
			"ssh_user": schema.StringAttribute{
				MarkdownDescription: "Default SSH username to create in VMs (can be overridden per VM)",
				Optional:            true,
			},
			"ssh_public_key_file": schema.StringAttribute{
				MarkdownDescription: "Path to SSH public key file to inject into VMs (can be overridden per VM)",
				Optional:            true,
			},
		},
	}
}

func (p *RcloudProvider) Configure(ctx context.Context, req provider.ConfigureRequest, resp *provider.ConfigureResponse) {
	var data RcloudProviderModel

	resp.Diagnostics.Append(req.Config.Get(ctx, &data)...)

	if resp.Diagnostics.HasError() {
		return
	}

	// Configuration values are now available.
	// if data.Endpoint.IsNull() { /* ... */ }

	// Default to environment variable or localhost
	endpoint := os.Getenv("RCLOUD_ENDPOINT")
	if !data.Endpoint.IsNull() {
		endpoint = data.Endpoint.ValueString()
	}
	if endpoint == "" {
		endpoint = "http://localhost:8765"
	}

	token := os.Getenv("RCLOUD_TOKEN")
	if !data.Token.IsNull() {
		token = data.Token.ValueString()
	}

	// SSH configuration
	sshUser := ""
	if !data.SSHUser.IsNull() {
		sshUser = data.SSHUser.ValueString()
	}

	sshPublicKeyFile := ""
	if !data.SSHPublicKeyFile.IsNull() {
		sshPublicKeyFile = data.SSHPublicKeyFile.ValueString()
	}

	// Create API client
	client := &APIClient{
		Endpoint:         endpoint,
		Token:            token,
		SSHUser:          sshUser,
		SSHPublicKeyFile: sshPublicKeyFile,
	}

	resp.DataSourceData = client
	resp.ResourceData = client
}

func (p *RcloudProvider) Resources(ctx context.Context) []func() resource.Resource {
	return []func() resource.Resource{
		NewVMResource,
	}
}

func (p *RcloudProvider) DataSources(ctx context.Context) []func() datasource.DataSource {
	return []func() datasource.DataSource{
		// NewImageDataSource,
	}
}

func New(version string) func() provider.Provider {
	return func() provider.Provider {
		return &RcloudProvider{
			version: version,
		}
	}
}
