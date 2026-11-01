helm repo add kedacore https://kedacore.github.io/charts  
helm repo update
helm upgrade --install keda --version 2.20.1 kedacore/keda --namespace keda --create-namespace


