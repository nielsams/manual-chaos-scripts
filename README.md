# manual-chaos-scripts

## What's this?
A collection of Chaos experiments that can run standalone, used to validate specific failure scenarios in Azure applications

## Usage

- Clone the repository
- Make changes to the main.py file to update global parameters, as well as the parameters for the experiments you want to target. Experiments you don't need you can set to 'False' on the first line.
- Run 'az login' and ensure you have permissions to perform the selected actions
- Run 'python3 main.py'

## Available Experiments

1) Kill AKS pods (gracefully or not) by label selector
2) AKS Zone Down Simulation
3) Temporarily Block network connectivity between subnets
4) AKS Network Partition
5) Forced or graceful failover of a Postgres Flexible server 
