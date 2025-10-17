use anyhow::{Context, Result};
use serde::Serialize;
use std::path::Path;
use tera::{Context as TeraContext, Tera};
use tracing::info;

/// Template context for VM XML generation
#[derive(Debug, Serialize)]
pub struct VmXmlContext {
    pub hostname: String,
    pub libvirt_mem_mb: u64,
    pub libvirt_vcpus_count: u32,
    pub kdevops_storage_pool_path: String,
    pub guestfs_path: String,
    pub libvirt_session_public_network_dev: String,
    pub qemu_bin_path: String,
    pub guestfs_requires_uefi: bool,
    pub libvirt_host_passthrough: bool,
    pub libvirt_enable_gdb: bool,
}

impl VmXmlContext {
    #[allow(dead_code)]
    pub fn new(
        vm_name: &str,
        vcpus: u32,
        memory_mb: u64,
        storage_pool_path: &Path,
        network_bridge: &str,
    ) -> Self {
        Self {
            hostname: vm_name.to_string(),
            libvirt_mem_mb: memory_mb,
            libvirt_vcpus_count: vcpus,
            kdevops_storage_pool_path: storage_pool_path.display().to_string(),
            guestfs_path: storage_pool_path.display().to_string(),
            libvirt_session_public_network_dev: network_bridge.to_string(),
            qemu_bin_path: "/usr/bin/qemu-system-x86_64".to_string(),
            guestfs_requires_uefi: false,
            libvirt_host_passthrough: true,
            libvirt_enable_gdb: false,
        }
    }
}

/// Render libvirt XML from guestfs template
#[allow(dead_code)]
pub fn render_vm_xml(template_path: &Path, context: &VmXmlContext) -> Result<String> {
    info!(
        "Rendering VM XML from template: {}",
        template_path.display()
    );

    // Load template
    let template_str = std::fs::read_to_string(template_path)
        .with_context(|| format!("Failed to read template {}", template_path.display()))?;

    // Create Tera instance
    let mut tera = Tera::default();
    tera.add_raw_template("vm.xml", &template_str)
        .context("Failed to parse template")?;

    // Create context
    let mut tera_context = TeraContext::new();
    tera_context.insert("hostname", &context.hostname);
    tera_context.insert("libvirt_mem_mb", &context.libvirt_mem_mb);
    tera_context.insert("libvirt_vcpus_count", &context.libvirt_vcpus_count);
    tera_context.insert(
        "kdevops_storage_pool_path",
        &context.kdevops_storage_pool_path,
    );
    tera_context.insert("guestfs_path", &context.guestfs_path);
    tera_context.insert(
        "libvirt_session_public_network_dev",
        &context.libvirt_session_public_network_dev,
    );
    tera_context.insert("qemu_bin_path", &context.qemu_bin_path);
    tera_context.insert("guestfs_requires_uefi", &context.guestfs_requires_uefi);
    tera_context.insert(
        "libvirt_host_passthrough",
        &context.libvirt_host_passthrough,
    );
    tera_context.insert("libvirt_enable_gdb", &context.libvirt_enable_gdb);

    // Render template
    let xml = tera
        .render("vm.xml", &tera_context)
        .context("Failed to render template")?;

    info!("Successfully rendered VM XML ({} bytes)", xml.len());
    Ok(xml)
}

/// Simplified XML generation for testing (without template)
pub fn generate_simple_vm_xml(
    vm_name: &str,
    vcpus: u32,
    memory_mb: u64,
    disk_path: &Path,
    network_name: &str,
    requires_uefi: bool,
) -> String {
    // Determine firmware configuration based on UEFI requirement
    let (os_section, firmware_feature) = if requires_uefi {
        (
            r#"  <os firmware='efi'>
    <type arch='x86_64' machine='q35'>hvm</type>
    <boot dev='hd'/>
  </os>"#,
            "    <smm state='on'/>",
        )
    } else {
        (
            r#"  <os>
    <type arch='x86_64' machine='q35'>hvm</type>
    <boot dev='hd'/>
  </os>"#,
            "",
        )
    };

    format!(
        r#"<domain type='kvm'>
  <name>{}</name>
  <memory unit='MiB'>{}</memory>
  <vcpu placement='static'>{}</vcpu>
{}
  <features>
    <acpi/>
    <apic/>
{}
  </features>
  <cpu mode='host-passthrough'/>
  <clock offset='localtime'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='none' io='native'/>
      <source file='{}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <source network='{}'/>
      <model type='virtio'/>
    </interface>
    <serial type='pty'>
      <target type='isa-serial' port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <memballoon model='virtio'/>
    <rng model='virtio'>
      <backend model='random'>/dev/urandom</backend>
    </rng>
  </devices>
</domain>"#,
        vm_name,
        memory_mb,
        vcpus,
        os_section,
        firmware_feature,
        disk_path.display(),
        network_name
    )
}
