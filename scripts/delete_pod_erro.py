import os
from kubernetes import client, config
from kubernetes.client.rest import ApiException

def main():
    # Carrega a configuração do Kubernetes. 
    # Em ambiente local/GitHub Actions, usamos o kubeconfig configurado.
    try:
        config.load_kube_config()
    except Exception:
        print("Não foi possível carregar o kubeconfig local. Tentando configuração interna...")
        config.load_incluster_config()

    v1 = client.CoreV1Api()
    
    # Define quais status de Pod nós queremos eliminar
    STATUS_PARA_DELETAR = ["Failed", "Error", "CrashLoopBackOff"]
    
    print("Buscando pods com problemas em todos os namespaces...")
    
    try:
        # Listar todos os pods de todos os namespaces
        pods = v1.list_pod_for_all_namespaces(watch=False)
        
        pods_deletados = 0
        
        for pod in pods.items:
            pod_name = pod.metadata.name
            namespace = pod.metadata.namespace
            
            # Pega o status geral ou o status dos containers internos
            pod_phase = pod.status.phase
            container_statuses = pod.status.container_statuses or []
            
            deve_deletar = False
            motivo = ""

            # 1. Verifica a fase geral do Pod
            if pod_phase in STATUS_PARA_DELETAR:
                deve_deletar = True
                motivo = pod_phase
            
            # 2. Verifica se algum container dentro do pod está travado em CrashLoop
            for status in container_statuses:
                if status.state.waiting and status.state.waiting.reason in STATUS_PARA_DELETAR:
                    deve_deletar = True
                    motivo = status.state.waiting.reason
                    break


            if deve_deletar:
                print(f"Deletando pod '{pod_name}' no namespace '{namespace}' (Motivo: {motivo})...")
                try:
                    v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
                    pods_deletados += 1
                except ApiException as e:
                    print(f"Erro ao deletar pod {pod_name}: {e}")
                    
        if pods_deletados == 0:
            print("Nenhum pod com erro foi encontrado.")
        else:
            print(f"Sucesso! Total de pods limpos: {pods_deletados}")

    except ApiException as e:
        print(f"Erro ao listar os pods: {e}")

if __name__ == "__main__":
    main()