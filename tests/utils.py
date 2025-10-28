#!/usr/bin/env python3

import subprocess
import logging

logger = logging.getLogger(__name__)


def run_command(command: str) -> tuple[str, int]:
    """
    Execute an Azure CLI command and return output and return code.
    
    Args:
        command: Azure CLI command to execute
        
    Returns:
        Tuple of (output, return_code)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.debug(f"Azure CLI command failed: {result.stderr}")

        return result.stdout, result.returncode
    except Exception as e:
        logger.error(f"Error executing Azure CLI command: {e}")
        return "", 1
    
def get_aks_credentials(resource_group: str, cluster_name: str) -> bool:
    """
    Get AKS cluster credentials using Azure CLI.
    
    Args:
        resource_group: The resource group of the AKS cluster
        cluster_name: The name of the AKS cluster
        
    Returns:
        True if successful, False otherwise
    """
    get_credentials_cmd = (
        f"az aks get-credentials "
        f"--resource-group {resource_group} "
        f"--name {cluster_name} "
        f"--overwrite-existing"
    )
    output, return_code = run_command(get_credentials_cmd)
    if return_code != 0:
        logger.error(f"Failed to get AKS credentials: {output}")
        return False
    
    logger.debug(f"AKS credentials obtained successfully for cluster '{cluster_name}' in resource group '{resource_group}'")
    return True

def kubectl_installed() -> bool:
    """
    Check if kubectl is installed and accessible.
    
    Returns:
        True if kubectl is installed, False otherwise
    """
    kubectl_check_cmd = "kubectl version --client"
    output, return_code = run_command(kubectl_check_cmd)
    return return_code == 0

def helm_installed() -> bool:
    """
    Check if Helm is installed and accessible.
    
    Returns:
        True if Helm is installed, False otherwise
    """
    helm_check_cmd = "helm version"
    output, return_code = run_command(helm_check_cmd)
    return return_code == 0

def chaos_mesh_installed() -> bool:
    """
    Check if Chaos Mesh is installed in the Kubernetes cluster.
    
    Returns:
        True if Chaos Mesh is installed, False otherwise
    """

    if not helm_installed():
        return False

    check_cmd = "helm status chaos-mesh -n chaos-testing"
    output, return_code = run_command(check_cmd)
    return return_code == 0

def install_chaos_mesh() -> bool:
    """
    Install Chaos Mesh in the Kubernetes cluster using Helm.
    
    Returns:
        True if installation was successful, False otherwise
    """

    install_chaos_mesh_cmds = [
        "helm repo add chaos-mesh https://charts.chaos-mesh.org && helm repo update",
        "kubectl get ns chaos-testing || kubectl create ns chaos-testing",
        (
            "helm install chaos-mesh chaos-mesh/chaos-mesh "
            "--namespace=chaos-testing "
            "--set chaosDaemon.runtime=containerd "
            "--set chaosDaemon.socketPath=/run/containerd/containerd.sock"
        )
    ]

    for cmd in install_chaos_mesh_cmds:
        output, return_code = run_command(cmd)
        if return_code != 0:
            logger.error(f"Failed to execute command '{cmd}': {output}")
            return False
        
    logger.debug("Chaos Mesh installed successfully.")