#!/usr/bin/env python3
import logging
import time
from tests.utils import run_command, helm_installed, kubectl_installed, chaos_mesh_installed, install_chaos_mesh, get_aks_credentials

logger = logging.getLogger(__name__)

def aks_container_network_partition(resource_group: str, cluster_name: str, namespace_name: str, isolated_zone: int, duration_seconds: int) -> bool:
    """
    Test function to simulate network faults in AKS containers.
    
    Args:
        cluster_name: Name of the AKS cluster
        resource_group: Resource group of the AKS cluster
    """

    try:
        if not get_aks_credentials(resource_group, cluster_name):
            logger.error(f"Failed to get AKS credentials.")
            return False

        if not kubectl_installed():
            logger.error(f"kubectl is not installed or not configured properly.")
            return False
        
        if not helm_installed():
            logger.error(f"Helm is not installed or not configured properly.")
            return False
        
        if not chaos_mesh_installed():
            logger.debug("Chaos Mesh not found on cluster, installing it now...")
            install_chaos_mesh()

        logger.debug(f"Finding all pods that run in zone {isolated_zone}...")
        
        # Get a list of pods in the namespace and their zones
        pods_in_zones_cmd = f"kubectl get pods -n '{namespace_name}' -o jsonpath='{{range .items[*]}}{{.metadata.namespace}}{{\"\\t\"}}{{.metadata.name}}{{\"\\t\"}}{{.spec.nodeName}}{{\"\\n\"}}{{end}}' | while read ns pod node; do zone=$(kubectl get node \"$node\" -o jsonpath='{{.metadata.labels.topology\\.kubernetes\\.io/zone}}'); echo \"$pod\\t$zone\"; done"
        pods_in_zones, return_code = run_command(pods_in_zones_cmd)
        logger.debug(f"Pods in zones:\n{pods_in_zones}")

        # Label each pod with its zone, we'll use this later as a selector
        for pod in pods_in_zones.strip().split("\n"):
            pod_name, pod_zone = pod.split("\t")

            # Isolate the zone number, we don't care about region here:
            pod_zone = pod_zone.split("-")[-1]
            
            logger.debug(f"Labeling pod {pod_name} with zone {pod_zone}...")
            label_cmd = f"kubectl label pod '{pod_name}' -n '{namespace_name}' topology.kubernetes.io/zone={pod_zone} --overwrite"
            output, return_code = run_command(label_cmd)
            if return_code != 0:
                logger.error(f"Failed to label pod {pod_name} with zone {pod_zone}: {output}")
                return False

        # Define the chaos mesh network partition experiment YAML
        target_zones = ["1", "2", "3"]
        target_zones.remove(str(isolated_zone))

        network_partition_yaml = f"""
            apiVersion: chaos-mesh.org/v1alpha1
            kind: NetworkChaos
            metadata:
                name: chaos-partition
            spec:
                action: partition
                mode: all
                selector:
                    namespaces:
                      - {namespace_name}
                    labelSelectors:
                      'topology.kubernetes.io/zone': '{isolated_zone}'
                direction: both
                target:
                    mode: all
                    selector:
                        namespaces:
                          - {namespace_name}
                        expressionSelectors:
                          - key: topology.kubernetes.io/zone
                            operator: In
                            values: {target_zones}
        """        

        # Start/apply the experiment
        logger.debug(f"Applying NetworkChaos experiment")
        apply_cmd = f"echo \"{network_partition_yaml}\" | kubectl apply -f -"
        output, return_code = run_command(apply_cmd)
        if return_code != 0:
            logger.error(f"Failed to apply NetworkChaos experiment: {output}")
            return False

        # Wait for the specified duration.
        logger.debug(f"Network partition applied, waiting for {duration_seconds}...")
        time.sleep(duration_seconds)

        # Clean up the experiment
        logger.debug(f"Deleting NetworkChaos experiment...")
        delete_cmd = "kubectl delete networkchaos chaos-partition"
        output, return_code = run_command(delete_cmd)
        if return_code != 0:
            logger.warning(f"Failed to delete NetworkChaos experiment: {output}. It may still be running, delete it manually!")
            return False


        return True

    except Exception as e:
        logger.error(f"Exception occurred while killing pods: {e}")
        return False