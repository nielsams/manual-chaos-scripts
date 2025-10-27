#!/usr/bin/env python3

import logging
import json
from tests.utils import run_azure_cli

logger = logging.getLogger(__name__)


def aks_zone_down(resource_group: str, cluster_name: str, target_zone: str) -> bool:
    """
    Simulate zone down by deleting all AKS nodes in a specific availability zone.
    
    This function retrieves all node pools in the AKS cluster, finds VMSS instances
    in the target zone, and deletes them to simulate zone failure.
    
    Args:
        resource_group: Name of the resource group containing the AKS cluster
        cluster_name: Name of the AKS cluster
        target_zone: Target availability zone (e.g., "1", "2", "3")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Starting zone down simulation for cluster '{cluster_name}' in zone '{target_zone}'")
        
        # Retrieve the node resource group for the AKS cluster
        show_cluster_cmd = (
            f"az aks show "
            f"--resource-group {resource_group} "
            f"--name {cluster_name} "
            f"--query nodeResourceGroup "
            f"-o tsv"
        )
        node_rg, return_code = run_azure_cli(show_cluster_cmd)
        logger.debug(f"Node resource group command output: {node_rg}")

        if return_code != 0:
            logger.error(f"Failed to retrieve node resource group for cluster '{cluster_name}'")
            return False
        
        node_rg = node_rg.strip()
        
        # List all node pools in the AKS cluster
        list_nodepools_cmd = (
            f"az aks nodepool list "
            f"--resource-group {resource_group} "
            f"--cluster-name {cluster_name} "
            f"-o json"
        )
        nodepools_output, return_code = run_azure_cli(list_nodepools_cmd)
        logger.debug(f"Node pools command output: {nodepools_output}")
        
        if return_code != 0:
            logger.error(f"Failed to list node pools for cluster '{cluster_name}'")
            return False
        
        # nodepools = [np.strip() for np in nodepools_output.strip().split('\n') if np.strip()]
        nodepools = json.loads(nodepools_output)
        logger.debug(f"Found {len(nodepools)} node pool(s)")
        
        # Process each node pool
        for nodepool in nodepools:
            logger.debug(f"Processing node pool: {nodepool['name']}")
            
            # Find VMSS whose name contains the node pool name
            list_vmss_cmd = (
                f"az vmss list "
                f"--resource-group {node_rg} "
                f"--query \"[?contains(name, '{nodepool['name']}')].name\" "
                f"-o tsv"
            )
            vmss_output, return_code = run_azure_cli(list_vmss_cmd)
            
            if return_code != 0:
                logger.warning(f"Failed to list VMSS for node pool '{nodepool['name']}'")
                continue
            
            vmss_names = [v.strip() for v in vmss_output.strip().split('\n') if v.strip()]
            
            if not vmss_names:
                logger.info(f"No VMSS found for node pool '{nodepool['name']}', skipping...")
                continue
            
            vmss_name = vmss_names[0]
            logger.debug(f"Found VMSS '{vmss_name}' for node pool '{nodepool['name']}'")

            # List VMSS instances in the target availability zone
            list_instances_cmd = (
                f"az vmss list-instances "
                f"--resource-group {node_rg} "
                f"--name {vmss_name} "
                f"--query \"[?zones[0]=='{target_zone}'].osProfile.computerName\" "
                f"-o tsv"
            )
            instances_output, return_code = run_azure_cli(list_instances_cmd)
            
            if return_code != 0:
                logger.warning(f"Failed to list instances for VMSS '{vmss_name}'")
                continue
            
            machine_names = [m.strip() for m in instances_output.strip().split('\n') if m.strip()]
            
            if machine_names:
                logger.info(f"Deleting {len(machine_names)} instance(s) in zone {target_zone} for node pool '{nodepool['name']}' from cluster '{cluster_name}'")
                
                # Delete the machines
                delete_machines_cmd = (
                    f"az aks nodepool delete-machines "
                    f"--resource-group {resource_group} "
                    f"--cluster-name {cluster_name} "
                    f"--nodepool-name {nodepool['name']} "
                    f"--machine-names {' '.join(machine_names)}"
                )
                _, return_code = run_azure_cli(delete_machines_cmd)
                
                if return_code != 0:
                    logger.error(f"Failed to delete machines in node pool '{nodepool['name']}'")
                    return False
                
                if nodepool['enableAutoScaling']:
                    logger.info(f"Machines were deleted from nodepool '{nodepool['name']}' on cluster '{cluster_name}'. Auto-scaling is enabled, so new nodes should be provisioned automatically within a few minutes.")
                else:
                    logger.info(f"Machines were deleted from nodepool '{nodepool['name']}' on cluster '{cluster_name}'. Auto-scaling is disabled; consider manually scaling the node pool to restore capacity.")

            else:
                logger.warning(f"No instances found in zone {target_zone} for node pool '{nodepool['name']}'.")

        return True
        
    except Exception as e:
        logger.error(f"Error in aks_zone_down: {e}")
        return False
