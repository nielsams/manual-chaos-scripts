#!/bin/bash

# Deploy Hello World Application to Kubernetes
# Usage: ./deploy_hello_world.sh <namespace>
# Example: ./deploy_hello_world.sh hello-world-ns

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if kubectl is available and configured
check_kubectl() {
    print_status "Checking kubectl configuration..."
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        print_error "kubectl is not configured or cluster is not accessible"
        exit 1
    fi
    
    print_success "kubectl is configured and cluster is accessible"
}

# Function to create namespace if it doesn't exist
create_namespace() {
    local namespace=$1
    
    print_status "Checking if namespace '$namespace' exists..."
    
    if kubectl get namespace "$namespace" &> /dev/null; then
        print_warning "Namespace '$namespace' already exists"
    else
        print_status "Creating namespace '$namespace'..."
        kubectl create namespace "$namespace"
        print_success "Namespace '$namespace' created successfully"
    fi
}

# Function to deploy hello world application
deploy_hello_world() {
    local namespace=$1
    local app_name="hello-world"
    local deployment_name="hello-world-deployment"
    local service_name="hello-world-service"
    
    print_status "Deploying hello world application to namespace '$namespace'..."
    
    # Create deployment
    cat <<EOF | kubectl apply -n "$namespace" -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $deployment_name
  labels:
    app: $app_name
spec:
  replicas: 3
  selector:
    matchLabels:
      app: $app_name
  template:
    metadata:
      labels:
        app: $app_name
    spec:
      containers:
      - name: hello-world
        image: nginx:latest
        ports:
        - containerPort: 80
        env:
        - name: MESSAGE
          value: "Hello World from Kubernetes!"
        volumeMounts:
        - name: html-volume
          mountPath: /usr/share/nginx/html
      volumes:
      - name: html-volume
        configMap:
          name: hello-world-html
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: hello-world-html
data:
  index.html: |
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hello World</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                padding: 50px;
                margin: 0;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 40px;
                backdrop-filter: blur(10px);
            }
            h1 {
                font-size: 3em;
                margin-bottom: 20px;
            }
            p {
                font-size: 1.2em;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Hello World! 🌍</h1>
            <p>Welcome to your Kubernetes deployment</p>
            <p>Namespace: $namespace</p>
            <p>Pod: <span id="hostname">Loading...</span></p>
        </div>
        <script>
            fetch('/api/hostname')
                .then(response => response.text())
                .then(hostname => {
                    document.getElementById('hostname').textContent = hostname;
                })
                .catch(() => {
                    document.getElementById('hostname').textContent = window.location.hostname;
                });
        </script>
    </body>
    </html>
---
apiVersion: v1
kind: Service
metadata:
  name: $service_name
  labels:
    app: $app_name
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
  selector:
    app: $app_name
EOF

    print_success "Hello world application deployed successfully!"
}

# Function to wait for deployment to be ready
wait_for_deployment() {
    local namespace=$1
    local deployment_name="hello-world-deployment"
    
    print_status "Waiting for deployment to be ready..."
    
    if kubectl wait --for=condition=available --timeout=300s deployment/$deployment_name -n "$namespace"; then
        print_success "Deployment is ready!"
    else
        print_error "Deployment failed to become ready within 5 minutes"
        exit 1
    fi
}

# Function to display deployment information
show_deployment_info() {
    local namespace=$1
    local service_name="hello-world-service"
    
    print_status "Deployment Information:"
    echo
    
    # Show pods
    echo -e "${BLUE}Pods:${NC}"
    kubectl get pods -n "$namespace" -l app=hello-world
    echo
    
    # Show service
    echo -e "${BLUE}Service:${NC}"
    kubectl get service "$service_name" -n "$namespace"
    echo
    
    # Try to get external IP (for LoadBalancer)
    print_status "Checking for external IP (this may take a few minutes for cloud load balancers)..."
    external_ip=$(kubectl get service "$service_name" -n "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -n "$external_ip" ] && [ "$external_ip" != "null" ]; then
        print_success "Application is accessible at: http://$external_ip"
    else
        print_warning "External IP not yet assigned. You can check later with:"
        echo "kubectl get service $service_name -n $namespace"
        echo
        print_status "You can also access the application using port-forward:"
        echo "kubectl port-forward service/$service_name -n $namespace 8080:80"
        echo "Then visit: http://localhost:8080"
    fi
}

# Function to show cleanup instructions
show_cleanup_info() {
    local namespace=$1
    
    echo
    print_status "To clean up this deployment, run:"
    echo "kubectl delete namespace $namespace"
}

# Main function
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Kubernetes Hello World Deployment${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo
    
    # Check if namespace is provided
    if [ $# -eq 0 ]; then
        print_error "Usage: $0 <namespace>"
        print_error "Example: $0 hello-world-ns"
        exit 1
    fi
    
    local namespace=$1
    
    # Validate namespace name (Kubernetes naming requirements)
    if ! [[ "$namespace" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]]; then
        print_error "Invalid namespace name. Must contain only lowercase letters, numbers, and hyphens."
        print_error "Must start and end with alphanumeric characters."
        exit 1
    fi
    
    # Execute deployment steps
    check_kubectl
    create_namespace "$namespace"
    deploy_hello_world "$namespace"
    wait_for_deployment "$namespace"
    show_deployment_info "$namespace"
    show_cleanup_info "$namespace"
    
    echo
    print_success "Hello World application deployment completed successfully! 🎉"
}

# Run main function with all arguments
main "$@"