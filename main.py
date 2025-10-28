#!/usr/bin/env python3

import logging
import sys
from tests.block_network_access import block_network_access
from tests.aks_zone_down import aks_zone_down
from tests.postgres_failover import postgres_failover
from tests.aks_kill_pods import aks_kill_pods
from tests.aks_container_network_partition import aks_container_network_partition

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Main function to orchestrate zone redundancy experiments.

    """
    logger.info("\n\nStarting chaos experiments")    

    # Global Configuration
    resource_group = "test"


    #
    #
    # Experiment 1: Kill Pods in AKS Cluster
    if True:
        # Update these config values:
        cluster_name = "niels-aks-test-1"
        namespace_name = "chaos-test"
        label_selector = "app=hello-world"
        graceful_stop = False

        logger.info("Experiment 1: Kill pods in AKS cluster.")
        success = aks_kill_pods(resource_group, cluster_name, namespace_name, label_selector, graceful_stop)

        if success:
            logger.info("AKS pod kill experiment completed successfully\n\n")
        else:
            logger.error("AKS pod kill experiment failed")
    

    #
    #
    # Experiment 2: AKS Zone Down Simulation
    if True:
        # Update these config values:
        cluster_name = "niels-aks-test-1"

        logger.info("Experiment 2: Simulate AKS zone down.")
        success = aks_zone_down(resource_group, cluster_name, target_zone="1")

        if success:
            logger.info("AKS zone down simulation completed successfully\n\n")
        else:
            logger.error("AKS zone down simulation failed")


    #
    #
    # Experiment 3: Block Network access between two subnets
    if True:
        # Update these config values:
        vnet = "niels-test-vnet"
        subnet_source = "SubnetA"
        subnet_dest = "SubnetB"
        block_duration = 30  # seconds

        logger.info("Experiment 3: Block network access between subnets.")
        success = block_network_access(resource_group, vnet, subnet_source, subnet_dest, block_duration)
        
        if success:
            logger.info("Network blocking experiment completed successfully\n\n")
        else:
            logger.error("Network blocking experiment failed")    


    #
    #
    # Experiment 4: Container Network Partition in AKS
    if True:
        # Update these config values:
        cluster_name = "niels-aks-test-1"
        namespace_name = "hello-world"
        isolated_zone = 1
        block_duration = 60 # seconds

        # Note that this will install Chaos Mesh if not already installed
        logger.info("Experiment 4: Simulate container network faults in AKS.")
        success = aks_container_network_partition(resource_group, cluster_name, namespace_name, isolated_zone, block_duration)

        if success:
            logger.info("AKS container network faults experiment completed successfully\n\n")
        else:
            logger.error("AKS container network faults experiment failed")


    #
    #
    # Experiment 5: Postgres Failover
    if True:
        # Update these config values:
        database_name = "niels-test-pgdb"

        logger.info("Experiment 5: Simulate PostgreSQL failover.")
        success = postgres_failover(resource_group, database_name, forced_failover=True)

        if success:
            logger.info("PostgreSQL failover completed successfully\n\n")
        else:
            logger.error("PostgreSQL failover failed")




    #
    #
    # All Experiments Completed
    logger.info("All experiments completed")


if __name__ == "__main__":
    main()
