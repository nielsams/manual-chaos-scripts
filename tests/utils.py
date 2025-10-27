#!/usr/bin/env python3

import subprocess
import logging

logger = logging.getLogger(__name__)


def run_azure_cli(command: str) -> tuple[str, int]:
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
            logger.warning(f"Azure CLI command failed: {result.stderr}")

        return result.stdout, result.returncode
    except Exception as e:
        logger.error(f"Error executing Azure CLI command: {e}")
        return "", 1
