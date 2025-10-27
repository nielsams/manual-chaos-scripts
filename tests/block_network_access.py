#!/usr/bin/env python3

import time
import logging
from tests.utils import run_azure_cli

logger = logging.getLogger(__name__)

def block_network_access(resource_group: str, vnet: str, subnet_source: str, subnet_dest: str, duration_seconds: int) -> bool:
    """
    Block network connectivity between two subnets for a specified duration.
    
    Creates an NSG rule to block traffic between subnet_source and subnet_dest,
    waits for the specified duration, then removes the rule.
    
    Args:
        resource_group: Name of the resource group containing the NSG
        vnet: Name of the virtual network
        subnet_source: Name of the first subnet
        subnet_dest: Name of the second subnet
        duration_seconds: Duration to block network in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        rule_name = f"block-{subnet_source}-to-{subnet_dest}-rule"
        
        logger.info(f"Creating NSG rule to block traffic between {subnet_source} and {subnet_dest} for {duration_seconds} seconds")
        
        # Get all NSGs associated with the source subnet:
        get_nsg_cmd = f"az network vnet subnet show --resource-group {resource_group} --vnet-name {vnet} --name {subnet_source} --query \"networkSecurityGroup.id\" -o tsv"
        nsg_id, return_code = run_azure_cli(get_nsg_cmd)
        nsg_name = nsg_id.strip().split('/')[-1] if nsg_id else ''

        we_created_nsg = False

        # If no NSG is associated, create one and associate it:
        if return_code != 0 or not nsg_id.strip():
            logger.info(f"Could not find existing NSG for subnet {subnet_source} in resource group {resource_group}. We'll have to create one.")
            nsg_name = f"{subnet_source}-chaostest-nsg"
            create_nsg_cmd = f"az network nsg create --resource-group {resource_group} --name {nsg_name}"
            _, return_code = run_azure_cli(create_nsg_cmd)            

            if return_code != 0:
                logger.error(f"Failed to create NSG for subnet {subnet_source} in resource group {resource_group}")
                return False
            else:
                we_created_nsg = True
            
            # Associate our new NSG with the subnet:
            logger.debug(f"Associating newly created NSG with subnet {subnet_source} in resource group {resource_group}")
            associate_nsg_cmd = f"az network vnet subnet update --resource-group {resource_group} --vnet-name {vnet} --name {subnet_source} --network-security-group {nsg_name}"
            _, return_code = run_azure_cli(associate_nsg_cmd)

            if return_code != 0:
                logger.error(f"Failed to associate NSG with subnet {subnet_source} in resource group {resource_group}")
                return False

        # Get address prefixes for both subnets
        subnet_source_prefix, error_a = run_azure_cli(
            f"az network vnet subnet show --resource-group {resource_group} --vnet-name {vnet} --name {subnet_source} --query \"addressPrefix\" -o tsv"
        )
        subnet_dest_prefix, error_b = run_azure_cli(
            f"az network vnet subnet show --resource-group {resource_group} --vnet-name {vnet} --name {subnet_dest} --query \"addressPrefix\" -o tsv"
        )
        
        if error_a != 0 or error_b != 0:
            logger.error(f"Failed to retrieve address prefixes for subnets {subnet_source} or {subnet_dest}")
            return False
        
        logger.debug(f"Subnet {subnet_source} prefix: {subnet_source_prefix.strip()}, Subnet {subnet_dest} prefix: {subnet_dest_prefix.strip()}")
        logger.info(f"Adding temporary rule to NSG: {nsg_name}")
        
        # Create NSG rule to deny traffic
        create_rule_cmd = (
            f"az network nsg rule create "
            f"--resource-group {resource_group} "
            f"--nsg-name {nsg_name} "
            f"--name {rule_name} "
            f"--priority 100 "
            f"--direction Inbound "
            f"--access Deny "
            f"--protocol '*' "
            f"--source-address-prefixes {subnet_source_prefix.strip()} "
            f"--destination-address-prefixes {subnet_dest_prefix.strip()} "
            f"--destination-port-ranges '*' "
        )
        
        _, return_code = run_azure_cli(create_rule_cmd)
        if return_code != 0:
            logger.error(f"Failed to create NSG rule {rule_name}")
            return False
        
        logger.debug(f"NSG rule created successfully: {rule_name}")
        
        # Wait for specified duration
        logger.info(f"Network blocked for {duration_seconds} seconds starting now...")
        time.sleep(duration_seconds)
        
        # Remove the NSG rule
        delete_rule_cmd = (
            f"az network nsg rule delete "
            f"--resource-group {resource_group} "
            f"--nsg-name {nsg_name} "
            f"--name {rule_name} "
        )
        
        _, return_code = run_azure_cli(delete_rule_cmd)
        if return_code != 0:
            logger.error(f"Failed to delete NSG rule {rule_name}")
            return False
        
        # If we created the NSG, we should also remove it and disassociate it from the subnet
        if we_created_nsg:
            logger.debug(f"Cleaning up: Deleting NSG {nsg_name} and disassociating it from subnet {subnet_source}")
            # Disassociate NSG
            disassociate_nsg_cmd = f"az network vnet subnet update --resource-group {resource_group} --vnet-name {vnet} --name {subnet_source} --network-security-group null"
            _, return_code = run_azure_cli(disassociate_nsg_cmd)
            if return_code != 0:
                logger.error(f"Failed to disassociate NSG from subnet {subnet_source}")
                return False
            
            # Delete NSG
            delete_nsg_cmd = f"az network nsg delete --resource-group {resource_group} --name {nsg_name}"
            _, return_code = run_azure_cli(delete_nsg_cmd)
            if return_code != 0:
                logger.error(f"Failed to delete NSG {nsg_name}")
                return False
        
        logger.info(f"Network Blocking finished - NSG rule deleted successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Error in block_network_access: {e}")
        return False
