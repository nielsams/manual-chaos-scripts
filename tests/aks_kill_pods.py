#!/usr/bin/env python3
import logging
import json
from tests.utils import run_command, kubectl_installed, get_aks_credentials

logger = logging.getLogger(__name__)

def aks_kill_pods(resource_group: str, cluster_name: str, namespace_name: str, label_selector: str, graceful_stop: bool) -> bool:
    """
    Kill pods in an AKS cluster using a label selector.

    Args:
        resource_group: The resource group of the AKS cluster
        cluster_name: The name of the AKS cluster
        namespace_name: The namespace of the pods
        label_selector: The label selector to identify pods (e.g., "app=myapp")
        graceful_stop: Whether to perform a graceful stop

    Returns:
        True if successful, False otherwise
    """

    try:
        if not get_aks_credentials(resource_group, cluster_name):
            logger.error(f"Failed to get AKS credentials.")
            return False
        
        if not kubectl_installed():
            logger.error(f"kubectl is not installed or not configured properly.")
            return False

        # Construct the kubectl command to delete pods by label
        delete_pod_cmd = (
            f"kubectl delete pod "
            f"-l {label_selector} "
            f"-n {namespace_name} "
        )
        if graceful_stop:
            delete_pod_cmd += "--grace-period=30 "
        else:
            delete_pod_cmd += "--grace-period=0 --force "

        logger.debug(f"Executing command: {delete_pod_cmd}")
        output, return_code = run_command(delete_pod_cmd)
        if return_code != 0:
            logger.error(f"Failed to delete pods: {output}")
            return False

        logger.info(f"Pods with label '{label_selector}' in namespace '{namespace_name}' deleted successfully.")
        return True

    except Exception as e:
        logger.error(f"Exception occurred while killing pods: {e}")
        return False