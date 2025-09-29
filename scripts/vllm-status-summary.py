#!/usr/bin/env python3
"""
Simplified vLLM deployment status summary.
Parses verbose ansible output and presents a clean status overview.
"""

import sys
import re
from datetime import datetime


def parse_status_output(lines):
    """Parse the verbose status output and extract key information."""
    status = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ansible_running": False,
        "nodes": {},
        "overall_state": "unknown",
        "docker_images": {},
        "helm_values": {},
        "services": {},
    }

    current_section = None
    current_node = None

    for line in lines:
        # Track sections
        if "--- Ansible Process ---" in line:
            current_section = "ansible"
        elif "--- Helm Deployment" in line:
            current_section = "helm"
        elif "--- Kubernetes Cluster Status ---" in line:
            current_section = "k8s_cluster"
        elif "--- Kubernetes Pods ---" in line:
            current_section = "k8s_pods"
        elif "--- Docker Containers ---" in line:
            current_section = "docker"
        elif "--- Docker Mirror 9P Mount ---" in line:
            current_section = "9p_mount"
        elif "--- Docker Images" in line:
            current_section = "docker_images"
        elif "--- Helm Values" in line:
            current_section = "helm_values"
        elif "--- Kubernetes Services ---" in line:
            current_section = "k8s_services"

        # Parse node names
        if "| CHANGED |" in line or "| FAILED |" in line:
            match = re.match(r"^(\S+)\s+\|", line)
            if match:
                current_node = match.group(1)
                if current_node not in status["nodes"] and current_node != "localhost":
                    status["nodes"][current_node] = {
                        "helm_deploying": False,
                        "k8s_ready": False,
                        "minikube_running": False,
                        "docker_mirror_9p": False,
                        "pods_running": 0,
                        "pods_pending": 0,
                    }

        # Ansible process detection
        if (
            current_section == "ansible"
            and "ansible-playbook" in line
            and "vllm" in line
        ):
            status["ansible_running"] = True

        # Helm deployment detection
        if current_section == "helm" and current_node and current_node != "localhost":
            if "/usr/local/bin/helm upgrade" in line and "vllm" in line:
                status["nodes"][current_node]["helm_deploying"] = True

        # Kubernetes cluster status
        if (
            current_section == "k8s_cluster"
            and current_node
            and current_node != "localhost"
        ):
            if "Kubernetes control plane is running" in line:
                status["nodes"][current_node]["k8s_ready"] = True
            elif "connection refused" in line or "unreachable" in line:
                status["nodes"][current_node]["k8s_ready"] = False

        # Docker containers - detect minikube
        if current_section == "docker" and current_node and current_node != "localhost":
            if "minikube" in line and "Up" in line:
                status["nodes"][current_node]["minikube_running"] = True

        # 9P mount detection
        if (
            current_section == "9p_mount"
            and current_node
            and current_node != "localhost"
        ):
            if "kdevops_9p_docker_mirror" in line and "/mirror/docker" in line:
                status["nodes"][current_node]["docker_mirror_9p"] = True

        # Pod counting
        if (
            current_section == "k8s_pods"
            and current_node
            and current_node != "localhost"
        ):
            if re.search(r"\s+Running\s+", line):
                status["nodes"][current_node]["pods_running"] += 1
            elif re.search(r"\s+Pending\s+", line):
                status["nodes"][current_node]["pods_pending"] += 1

        # Docker images detection
        if (
            current_section == "docker_images"
            and current_node
            and current_node != "localhost"
        ):
            # Look for vllm or openeuler images
            if (
                ("vllm" in line.lower() or "openeuler" in line.lower())
                and "REPOSITORY" not in line
                and "|" not in line
            ):
                # Parse docker images output: REPOSITORY TAG IMAGE_ID CREATED SIZE
                parts = line.split()
                if len(parts) >= 2 and parts[0] not in [
                    "REPOSITORY",
                    "No",
                    "Unable",
                    "---",
                ]:
                    # Validate it looks like a real image (has slashes or well-known names)
                    if "/" in parts[0] or parts[0] in ["vllm", "openeuler"]:
                        image_name = f"{parts[0]}:{parts[1]}"
                        if current_node not in status["docker_images"]:
                            status["docker_images"][current_node] = []
                        if image_name not in status["docker_images"][current_node]:
                            status["docker_images"][current_node].append(image_name)

        # Helm values detection
        if (
            current_section == "helm_values"
            and current_node
            and current_node != "localhost"
        ):
            if "repository:" in line:
                match = re.search(r'repository:\s*["\']?([^"\']+)["\']?', line)
                if match:
                    if current_node not in status["helm_values"]:
                        status["helm_values"][current_node] = {
                            "images": [],
                            "model": None,
                        }
                    # Store repository for next tag
                    status["helm_values"][current_node]["_pending_repo"] = match.group(
                        1
                    )
            elif "tag:" in line:
                match = re.search(r'tag:\s*["\']?([^"\']+)["\']?', line)
                if match:
                    if current_node not in status["helm_values"]:
                        status["helm_values"][current_node] = {
                            "images": [],
                            "model": None,
                        }
                    # Combine with pending repository
                    repo = status["helm_values"][current_node].get(
                        "_pending_repo", "unknown"
                    )
                    tag = match.group(1)
                    full_image = f"{repo}:{tag}"
                    if full_image not in status["helm_values"][current_node]["images"]:
                        status["helm_values"][current_node]["images"].append(full_image)
                    status["helm_values"][current_node]["_pending_repo"] = None
            elif "modelURL:" in line:
                match = re.search(r'modelURL:\s*["\']?([^"\']+)["\']?', line)
                if match:
                    if current_node not in status["helm_values"]:
                        status["helm_values"][current_node] = {
                            "images": [],
                            "model": None,
                        }
                    status["helm_values"][current_node]["model"] = match.group(1)

        # Kubernetes services detection
        if (
            current_section == "k8s_services"
            and current_node
            and current_node != "localhost"
        ):
            # Look for vllm services with ClusterIP
            if "vllm" in line.lower() and "ClusterIP" in line:
                parts = line.split()
                if len(parts) >= 4:
                    svc_name = parts[0]
                    cluster_ip = parts[2]
                    ports = parts[4] if len(parts) > 4 else "unknown"
                    if current_node not in status["services"]:
                        status["services"][current_node] = []
                    status["services"][current_node].append(
                        {"name": svc_name, "ip": cluster_ip, "ports": ports}
                    )

    # Determine overall state
    if status["ansible_running"]:
        if any(n["helm_deploying"] for n in status["nodes"].values()):
            status["overall_state"] = "deploying"
        else:
            status["overall_state"] = "configuring"
    elif any(
        n["k8s_ready"] and n["pods_running"] > 0 for n in status["nodes"].values()
    ):
        status["overall_state"] = "running"
    elif any(n["minikube_running"] for n in status["nodes"].values()):
        status["overall_state"] = "starting"
    else:
        status["overall_state"] = "stopped"

    return status


def print_simplified_status(status):
    """Print a clean, simplified status summary."""

    # Header
    print("=" * 60)
    print(f"vLLM Deployment Status - {status['timestamp']}")
    print("=" * 60)
    print()

    # Overall status with emoji
    state_emoji = {
        "running": "✅",
        "deploying": "🚀",
        "configuring": "⚙️",
        "starting": "⏳",
        "stopped": "⏸️",
        "unknown": "❓",
    }

    state_desc = {
        "running": "Running and Ready",
        "deploying": "Deploying with Helm",
        "configuring": "Configuring Infrastructure",
        "starting": "Starting Services",
        "stopped": "Stopped",
        "unknown": "Unknown State",
    }

    emoji = state_emoji.get(status["overall_state"], "❓")
    desc = state_desc.get(status["overall_state"], "Unknown")

    print(f"Overall Status: {emoji} {desc}")
    print()

    # Ansible status
    if status["ansible_running"]:
        print("📦 Ansible: Running deployment playbook")
    else:
        print("📦 Ansible: Idle")
    print()

    # Per-node status
    if status["nodes"]:
        print("Nodes:")
        print("-" * 60)
        for node_name, node_info in sorted(status["nodes"].items()):
            print(f"\n  {node_name}:")

            # Helm status
            if node_info["helm_deploying"]:
                print("    🚀 Helm: Deploying vLLM production stack...")
            else:
                print("    📊 Helm: Idle")

            # Kubernetes status
            if node_info["k8s_ready"]:
                print("    ✅ Kubernetes: Cluster ready")
            elif node_info["minikube_running"]:
                print("    ⏳ Kubernetes: Cluster starting...")
            else:
                print("    ⏸️  Kubernetes: Not ready")

            # Pods
            if node_info["pods_running"] > 0:
                print(f"    🎯 Pods: {node_info['pods_running']} running", end="")
                if node_info["pods_pending"] > 0:
                    print(f", {node_info['pods_pending']} pending")
                else:
                    print()
            elif node_info["pods_pending"] > 0:
                print(f"    ⏳ Pods: {node_info['pods_pending']} pending")

            # Docker mirror
            if node_info["docker_mirror_9p"]:
                print("    🔗 Docker Mirror: Connected via 9P")
            else:
                print("    🌐 Docker Mirror: Not available")

    # Docker images section (only show if there are actual images)
    has_images = any(images for images in status["docker_images"].values() if images)
    if has_images:
        print()
        print("Docker Images (vLLM-related):")
        print("-" * 60)
        for node_name, images in sorted(status["docker_images"].items()):
            if images:  # Only show nodes with images
                print(f"\n  {node_name}:")
                for img in images[:5]:  # Show first 5 images
                    print(f"    📦 {img}")
                if len(images) > 5:
                    print(f"    ... and {len(images) - 5} more")

    # Helm configuration section
    if status["helm_values"]:
        print()
        print("Helm Configuration (Images to Deploy):")
        print("-" * 60)
        for node_name, values in sorted(status["helm_values"].items()):
            print(f"\n  {node_name}:")
            if "images" in values and values["images"]:
                for img in values["images"]:
                    # Identify image type
                    if "vllm-cpu" in img or "vllm-openai" in img:
                        print(f"    🚀 Engine: {img}")
                    elif "router" in img:
                        print(f"    🔀 Router: {img}")
                    else:
                        print(f"    📦 Image: {img}")
            if "model" in values and values["model"]:
                print(f"    🤖 Model: {values['model']}")

    # Services and test commands section
    if status["services"]:
        print()
        print("Services & Testing:")
        print("-" * 60)
        for node_name, services in sorted(status["services"].items()):
            print(f"\n  {node_name}:")
            router_svc = None
            engine_svc = None
            for svc in services:
                if "router" in svc["name"]:
                    router_svc = svc
                    print(f"    🔀 Router: {svc['name']}")
                    print(f"       IP: {svc['ip']}, Ports: {svc['ports']}")
                elif "engine" in svc["name"]:
                    engine_svc = svc
                    print(f"    🚀 Engine: {svc['name']}")
                    print(f"       IP: {svc['ip']}, Ports: {svc['ports']}")

            # Provide test commands
            if router_svc:
                node_short = node_name.replace("lpc-", "").replace("-dev", "")
                print(f"\n    📝 Test via kubectl port-forward:")
                print(f"       # Start port forward (run in background):")
                print(
                    f"       ssh {node_name} 'sudo KUBECONFIG=/root/.kube/config kubectl port-forward -n vllm-system \\"
                )
                print(f"         svc/{router_svc['name']} 8000:80 --address=0.0.0.0 &'")
                print(f"\n       # Test API (list models):")
                print(f"       curl http://{node_name}:8000/v1/models")
                print(f"\n       # Text completion example:")
                print(f"       curl http://{node_name}:8000/v1/completions \\")
                print(f"         -H 'Content-Type: application/json' \\")
                print(f"         -d '{{")
                print(f'           "model": "facebook/opt-125m",')
                print(f'           "prompt": "The meaning of life is",')
                print(f'           "max_tokens": 50')
                print(f"         }}'")
                print(f"\n       Note: Use /v1/completions (not /v1/chat/completions)")
                print(f"       as this model doesn't have a chat template configured.")

    print()
    print("=" * 60)

    # Helpful next steps based on state
    if status["overall_state"] == "deploying":
        print("\n💡 Deployment in progress. Helm may take 10-30 minutes.")
        print("   Run 'make vllm-status-simplified' again to check progress.")
    elif status["overall_state"] == "running":
        print("\n💡 Deployment complete! Next steps:")
        print("   - Use the test commands above to query the model")
        print("   - make vllm-monitor     (View monitoring dashboards)")
        print("   - make vllm-benchmark   (Run performance tests)")
    elif status["overall_state"] == "starting":
        print("\n💡 Kubernetes is starting. This may take a few minutes.")
    elif status["overall_state"] == "stopped":
        print("\n💡 vLLM is not running. To deploy:")
        print("   - make vllm             (Deploy vLLM stack)")

    print()


def main():
    """Main entry point."""
    lines = sys.stdin.readlines()
    status = parse_status_output(lines)
    print_simplified_status(status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
