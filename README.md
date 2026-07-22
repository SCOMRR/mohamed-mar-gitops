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

\`\`\`bash
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
\`\`\`

## 2. Initialisation du control-plane (sur `mohamedmar-master`)

\`\`\`bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=192.168.1.23

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml

kubeadm token create --print-join-command
\`\`\`

## 3. Rejoindre les workers

\`\`\`bash
sudo kubeadm join 192.168.1.23:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
\`\`\`

Vérification :
\`\`\`bash
kubectl get nodes -o wide
# mohamedmar-master, k8s-worker1, k8s-worker2 → Ready
\`\`\`

## 4. Helm + Argo CD (sur `mohamedmar-master`)

\`\`\`bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml --server-side

kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}'
kubectl get svc argocd-server -n argocd

kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
\`\`\`

Accès : `https://192.168.1.23:<port_443>` — user `admin`

## 5. Dépôt Git (GitHub)

\`\`\`bash
git init
git remote add origin https://github.com/scomrr/mohamed-mar-gitops.git
git add .
git commit -m "Initial commit - plateforme GitOps Mohamed-MAR"
git branch -M main
git push -u origin main
\`\`\`

## 6. Déployer l'Application Argo CD

\`\`\`bash
kubectl apply -f argocd/namespace.yaml
kubectl apply -f argocd/application.yaml

kubectl get application -n argocd
\`\`\`

Argo CD observe le dépôt Git et synchronise automatiquement le chart Helm dans le namespace `mohamed-mar` (auto-sync + self-heal activés).

## 7. Vérifier l'application

\`\`\`bash
kubectl get pods -n mohamed-mar
kubectl get svc -n mohamed-mar
\`\`\`

Application exposée en **NodePort** (`30080`) :

http://192.168.1.23:30080

## 8. Observabilité (VM `mohamedmar-monitoring` dédiée, hors cluster)

### Prometheus + Grafana (Docker Compose)

Sur `mohamedmar-monitoring` :
\`\`\`bash
cd ~/monitoring-stack
docker compose up -d
\`\`\`
→ Prometheus sur le port `9090`, Grafana sur le port `3000`.

### node-exporter (métriques système des 3 nœuds K8s)

Installé en service systemd sur `mohamedmar-master`, `k8s-worker1`, `k8s-worker2` (port `9100`), scrapé par Prometheus à distance.

### Loki + Promtail (logs)

Loki tourne en conteneur Docker sur la VM monitoring (port `3100`). Promtail est installé en service systemd sur les 3 nœuds du cluster et pousse les logs des pods vers Loki.

### OpenTelemetry (traces)

Collector déployé dans le cluster (`observability/otel-collector.yaml`, namespace `mohamed-mar`). L'application Flask est instrumentée avec le SDK OpenTelemetry (`opentelemetry-instrumentation-flask`) et exporte ses traces vers le collector en gRPC.

### Dashboard Grafana personnalisé

`Mohamed-MAR - GitOps App Dashboard` — 3 panneaux : CPU cluster, RAM cluster, requêtes HTTP de l'application.

## 9. Test du rollback (Git revert)

Procédure réellement testée et validée :
\`\`\`bash
# 1. Introduction volontaire d'un tag d'image invalide dans values.yaml
git add helm/mohamed-mar-app/values.yaml
git commit -m "test: panne volontaire pour rollback [skip ci]"
git push
# → Argo CD synchronise, pod en ImagePullBackOff, app "Degraded"

# 2. Rollback via git revert
git revert <hash_du_commit> --no-edit
git push
# → Argo CD resynchronise automatiquement, app "Healthy" à nouveau
\`\`\`

## 10. Tests réalisés

- `helm lint helm/mohamed-mar-app` (job CI `helm-lint`)
- Scan de vulnérabilités Trivy à chaque build (job CI `build-and-push`)
- Panne volontaire (tag d'image invalide) + rollback via `git revert` réussi
- Vérification des logs applicatifs dans Grafana via Loki (Explore → Loki → `{job="mohamed-mar-logs"}`)
- Vérification des traces dans les logs du collector OpenTelemetry
- Génération de trafic HTTP et observation en temps réel dans le dashboard Grafana

---

## Structure du dépôt
## Liens

- **Dépôt Git :** https://github.com/scomrr/mohamed-mar-gitops
- **Application :** http://192.168.1.23:30080 (accessible depuis le réseau local)
