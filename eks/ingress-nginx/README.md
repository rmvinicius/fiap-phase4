helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx --version 4.15.1 ingress-nginx/ingress-nginx --namespace ingress --create-namespace -f values.yaml
kubectl apply -f ingress.yaml