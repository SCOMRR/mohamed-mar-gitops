# Plateforme GitOps observable sur Kubernetes — Mohamed MAR

**Étudiant :** Mohamed MAR
**Projet :** Plateforme GitOps observable sur Kubernetes (1 control-plane + 2 workers)

Dépôt Git source de vérité pour le déploiement automatisé, sécurisé et observable de l'application `mohamed-mar-app` sur un cluster Kubernetes à 3 nœuds.

**Stack réelle :** kubeadm (VMware, 4 VMs Ubuntu Server 22.04) → GitHub Actions (CI + GHCR + Trivy) → Argo CD (GitOps) → Prometheus/Grafana + Loki/Promtail + OpenTelemetry (observabilité, sur VM dédiée)

---

## 0. Architecture — 4 VMs (VMware)

| Nom | Rôle | CPU | RAM | Disque |
|---|---|---|---|---|
| `mohamedmar-master` | control-plane K8s | 2 | 2 Go | 25 Go |
| `k8s-worker1` | worker K8s | 2 | 2 Go | 25 Go |
| `k8s-worker2` | worker K8s | 2 | 2 Go | 25 Go |
| `mohamedmar-monitoring` | Prometheus + Grafana + Loki (hors cluster, en Docker) | 2 | 2,5 Go | 20 Go |

Réseau VMware : mode **Bridged**, les 4 VMs communiquent entre elles et ont accès à Internet.

---

## 1. Préparation des 3 nœuds du cluster (master + 2 workers)

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

cat <<EOC | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOC
sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOC | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOC
sudo sysctl --system

sudo apt update && sudo apt install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd

sudo apt install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt update
sudo apt install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

## 2. Initialisation du control-plane (sur `mohamedmar-master`)

```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=192.168.1.23

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml

kubeadm token create --print-join-command
```

## 3. Rejoindre les workers

```bash
sudo kubeadm join 192.168.1.23:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
```

Vérification :
```bash
kubectl get nodes -o wide
# mohamedmar-master, k8s-worker1, k8s-worker2 → Ready
```

## 4. Helm + Argo CD (sur `mohamedmar-master`)

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml --server-side

kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}'
kubectl get svc argocd-server -n argocd

kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Accès : `https://192.168.1.23:<port_443>` — user `admin`

## 5. Dépôt Git (GitHub)

```bash
git init
git remote add origin https://github.com/scomrr/mohamed-mar-gitops.git
git add .
git commit -m "Initial commit - plateforme GitOps Mohamed-MAR"
git branch -M main
git push -u origin main
```

## 6. Déployer l'Application Argo CD

```bash
kubectl apply -f argocd/namespace.yaml
kubectl apply -f argocd/application.yaml

kubectl get application -n argocd
```

Argo CD observe le dépôt Git et synchronise automatiquement le chart Helm dans le namespace `mohamed-mar` (auto-sync + self-heal activés).
cat > README.md << 'EOF'
# Plateforme GitOps observable sur Kubernetes — Mohamed MAR

**Étudiant :** Mohamed MAR
**Projet :** Plateforme GitOps observable sur Kubernetes (1 control-plane + 2 workers)

Dépôt Git source de vérité pour le déploiement automatisé, sécurisé et observable de l'application `mohamed-mar-app` sur un cluster Kubernetes à 3 nœuds.

**Stack réelle :** kubeadm (VMware, 4 VMs Ubuntu Server 22.04) → GitHub Actions (CI + GHCR + Trivy) → Argo CD (GitOps) → Prometheus/Grafana + Loki/Promtail + OpenTelemetry (observabilité, sur VM dédiée)

---

## 0. Architecture — 4 VMs (VMware)

| Nom | Rôle | CPU | RAM | Disque |
|---|---|---|---|---|
| `mohamedmar-master` | control-plane K8s | 2 | 2 Go | 25 Go |
| `k8s-worker1` | worker K8s | 2 | 2 Go | 25 Go |
| `k8s-worker2` | worker K8s | 2 | 2 Go | 25 Go |
| `mohamedmar-monitoring` | Prometheus + Grafana + Loki (hors cluster, en Docker) | 2 | 2,5 Go | 20 Go |

Réseau VMware : mode **Bridged**, les 4 VMs communiquent entre elles et ont accès à Internet.

---

## 1. Préparation des 3 nœuds du cluster (master + 2 workers)

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

cat <<EOC | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOC
sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOC | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOC
sudo sysctl --system

sudo apt update && sudo apt install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd

sudo apt install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt update
sudo apt install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

## 2. Initialisation du control-plane (sur `mohamedmar-master`)

```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=192.168.1.23

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml

kubeadm token create --print-join-command
```

## Liens

- **Dépôt Git :** https://github.com/scomrr/mohamed-mar-gitops
- **Application :** http://192.168.1.23:30080 (accessible depuis le réseau local)
