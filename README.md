# Plateforme GitOps observable sur Kubernetes — Mohamed MAR

Dépôt Git source de vérité pour le déploiement automatisé, sécurisé et observable
de l'application `mohamed-mar-app` sur un cluster Kubernetes à 3 nœuds.

**Stack :** kubeadm (VMware, 3 VMs) → GitHub Actions (CI + GHCR) → Argo CD (GitOps) → Prometheus/Grafana + Loki + OpenTelemetry (observabilité)

---

## 0. Prérequis matériel (VMware)

3 VMs Ubuntu Server 22.04 LTS :

| Nom          | Rôle           | CPU | RAM  | Disque |
|--------------|----------------|-----|------|--------|
| k8s-master   | control-plane  | 2   | 4 Go | 30 Go  |
| k8s-worker1  | worker         | 2   | 4 Go | 30 Go  |
| k8s-worker2  | worker         | 2   | 4 Go | 30 Go  |

Réseau VMware : mode **Bridged** (ou NAT + port forwarding) pour que les 3 VMs
se voient entre elles et aient accès à Internet.

---

## 1. Préparation des 3 VMs (à exécuter sur les 3 nœuds)

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# Modules kernel requis
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# Installation containerd
sudo apt update && sudo apt install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd

# Installation kubeadm, kubelet, kubectl
sudo apt install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt update
sudo apt install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

## 2. Initialisation du control-plane (sur k8s-master uniquement)

```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=<IP_MASTER>

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# CNI Calico
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml

# Récupérer la commande de join pour les workers
kubeadm token create --print-join-command
```

## 3. Rejoindre les workers (sur k8s-worker1 et k8s-worker2)

```bash
sudo kubeadm join <IP_MASTER>:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
```

Vérifier depuis le master :
```bash
kubectl get nodes -o wide
# Les 3 nœuds doivent apparaître en Ready
```

## 4. Installation de Helm et Argo CD (sur k8s-master)

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Exposer l'UI Argo CD
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}'
kubectl get svc argocd-server -n argocd

# Mot de passe admin initial
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

## 5. Créer le dépôt Git (GitHub)

```bash
gh repo create mohamed-mar-gitops --public --source=. --push
# ou manuellement : créer le repo sur github.com, puis
git init
git remote add origin https://github.com/<VOTRE_USER>/mohamed-mar-gitops.git
git add .
git commit -m "Initial commit - plateforme GitOps Mohamed-MAR"
git push -u origin main
```

⚠️ Avant de pousser, remplacer `VOTRE_USER_GITHUB` dans :
- `helm/mohamed-mar-app/values.yaml`
- `argocd/application.yaml`

## 6. Déployer l'Application Argo CD

```bash
kubectl apply -f argocd/namespace.yaml
kubectl apply -f argocd/application.yaml

# Vérifier la synchronisation
kubectl get application -n argocd
argocd app get mohamed-mar-release
```

Argo CD va observer le dépôt Git et déployer automatiquement le chart Helm
dans le namespace `mohamed-mar`.

## 7. Vérifier le déploiement de l'application

```bash
kubectl get pods -n mohamed-mar
kubectl get svc -n mohamed-mar

# Exposer temporairement pour tester
kubectl port-forward svc/mohamed-mar-release 8080:80 -n mohamed-mar
# puis ouvrir http://localhost:8080 → doit afficher "Mohamed-MAR"
```

## 8. Installer la stack d'observabilité

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Prometheus + Grafana
helm install prometheus prometheus-community/kube-prometheus-stack \
  -f observability/prometheus-values.yaml -n monitoring --create-namespace

# Loki (logs)
helm install loki grafana/loki-stack \
  -f observability/loki-values.yaml -n monitoring

# OpenTelemetry Collector (traces)
kubectl apply -f observability/otel-collector.yaml
```

Importer le dashboard personnalisé dans Grafana :
1. `kubectl get svc prometheus-grafana -n monitoring` (NodePort 32000)
2. Se connecter (admin / MohamedMar2026!)
3. Dashboards → New → Import → coller le contenu de
   `observability/grafana-dashboard-mohamed-mar.json`

## 9. Tester le cycle GitOps complet (rollback inclus)

```bash
# Modifier le code, commit, push → la CI build + push l'image + met à jour values.yaml
# → Argo CD détecte et synchronise automatiquement

# Voir l'historique des releases Helm
helm history mohamed-mar-release -n mohamed-mar

# Rollback manuel si besoin
helm rollback mohamed-mar-release 1 -n mohamed-mar
# ou via Argo CD UI : App → History and Rollback
```

## 10. Tests à réaliser pour le rapport

- [ ] `helm lint helm/mohamed-mar-app`
- [ ] Test de charge simple : `hey -z 30s http://<IP>:<PORT>/`
- [ ] Simuler une panne de pod : `kubectl delete pod <pod> -n mohamed-mar` → vérifier l'auto-réparation
- [ ] Modifier `replicaCount` dans Git → vérifier la synchronisation auto par Argo CD
- [ ] Rollback Helm et vérification dans Grafana (chute puis reprise des métriques)
- [ ] Vérifier les logs de l'app dans Grafana via Loki (Explore → Loki → `{namespace="mohamed-mar"}`)

---

## Structure du dépôt

```
.
├── app/                      # Code source de l'application
├── helm/mohamed-mar-app/     # Chart Helm (namespace, release: mohamed-mar)
├── .github/workflows/ci.yml  # Pipeline CI : build, test, lint, scan, push GHCR
├── argocd/                   # Manifests Argo CD (Application + Namespace)
└── observability/            # Prometheus, Grafana, Loki, OpenTelemetry
```
