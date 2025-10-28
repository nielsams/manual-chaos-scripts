#!/usr/bin/env python3
import logging
import json
from tests.utils import run_command

logger = logging.getLogger(__name__)

def postgres_failover(resource_group: str, database_name: str, forced_failover: bool) -> bool:
    """
    Failover a highly available PostgreSQL database to the secondary node.
    
    Args:
        resource_group: Name of the resource group containing the database
        database_name: Name of the PostgreSQL database
        force_failover: If True, perform immediate failover; if False, perform planned failover
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Starting PostgreSQL failover for database {database_name} in resource group {resource_group}. (Forced: {forced_failover})")
        
        # Check if the database exists and get its HA configuration
        get_db_cmd = (
            f"az postgres flexible-server show "
            f"--resource-group {resource_group} "
            f"--name {database_name} "
            f"-o json"
        )
        db_output, return_code = run_command(get_db_cmd)
        
        if return_code != 0:
            logger.error(f"Failed to retrieve database '{database_name}' in resource group '{resource_group}'")
            return False
        
        # Check if high availability is enabled
        db_info = json.loads(db_output)
        ha_enabled = db_info.get("highAvailability", {}).get("mode") == "ZoneRedundant"
        current_zone = db_info.get("availabilityZone", {})
        
        if not ha_enabled:
            logger.error(f"Database '{database_name}' is not configured for high availability")
            return False
        else:
            logger.info(f"Database '{database_name}' is HA enabled in zone {current_zone}")
        
        # Perform failover
        if forced_failover:
            failover_cmd = (
                f"az postgres flexible-server restart "
                f"--resource-group {resource_group} "
                f"--name {database_name} "
                f"--failover Forced"
            )
        else:
            failover_cmd = (
                f"az postgres flexible-server restart "
                f"--resource-group {resource_group} "
                f"--name {database_name} "
                f"--failover Planned"
            )
        logger.debug(f"Executing failover command: {failover_cmd}")
        _, return_code = run_command(failover_cmd)
        
        if return_code != 0:
            logger.error(f"Failed to failover database '{database_name}'")
            return False
        
        get_db_cmd = (
            f"az postgres flexible-server show "
            f"--resource-group {resource_group} "
            f"--name {database_name} "
            f"-o json"
        )
        db_output, return_code = run_command(get_db_cmd)
        db_info = json.loads(db_output)
        current_zone = db_info.get("availabilityZone", {})

        logger.info(f"Database '{database_name}' failover completed successfully. It is now in zone {current_zone}")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse database configuration: {e}")
        return False
    except Exception as e:
        logger.error(f"Error in postgres_failover: {e}")
        return False