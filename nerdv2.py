import os
import sys
import subprocess
import socket

def is_docker_environment():
    return os.path.exists('/.dockerenv')

def check_kernel_isolation():
    isolation_info = {
        "Namespaces": {},
        "Cgroups": {},
        "Capabilities": {}
    }

    # Comprobar namespaces
    available_namespaces = os.listdir('/proc/self/ns/')
    for namespace in ["cgroup", "ipc", "mnt", "net", "pid", "user", "uts"]:
        isolation_info["Namespaces"][namespace] = "Activated" if namespace in available_namespaces else "WARNING NOT ACTIVATED"

    # Comprobar cgroups
    available_cgroups = os.listdir('/sys/fs/cgroup/')
    for cgroup in ["cpu", "cpuacct", "blkio", "memory", "devices", "freezer", "net_cls", "perf_event", "net_prio", "hugetlb", "pids"]:
        isolation_info["Cgroups"][cgroup] = "Activated" if cgroup in available_cgroups else "WARNING NOT ACTIVATED"
    
    # Comprobar capabilities
    try:
        output = subprocess.check_output(['capsh', '--print'], universal_newlines=True)
        available_capabilities = output.split('\n')[1].split('=')[1].split()
        for capability in ["CAP_CHOWN", "CAP_DAC_OVERRIDE", "CAP_FSETID", "CAP_FOWNER", "CAP_MKNOD", "CAP_NET_RAW", "CAP_SETGID", "CAP_SETUID", "CAP_SETPCAP", "CAP_NET_BIND_SERVICE", "CAP_SYS_CHROOT", "CAP_KILL", "CAP_AUDIT_WRITE"]:
            isolation_info["Capabilities"][capability] = "Activated" if capability in available_capabilities else "WARNING NOT ACTIVATED"
    except:
        isolation_info["Capabilities"] = "capsh tool required for capability check"

    return isolation_info

def check_user_privileges():
    user_privileges_info = {
        "User ID": os.getuid(),
        "Group ID": os.getgid(),
        "In Sudo Group": "Yes" if os.system("groups $USER | grep -q '\\bsudo\\b'") == 0 else "No",
        "Sudo Permissions": subprocess.getoutput("sudo -l")
    }
    return user_privileges_info

def print_isolation_info(isolation_info):
    for isolation_type, info in isolation_info.items():
        print(f"{isolation_type}:")
        for item, status in info.items():
            status_color = '\033[92m' if "Activated" in status else '\033[91m'  # Verde para Activated, Rojo para WARNING NOT ACTIVATED
            print(f"    {item}: {status_color}{status}\033[0m")  # \033[0m resetea el color

def print_user_privileges_info(user_privileges_info):
    print("User Privileges:")
    for privilege, status in user_privileges_info.items():
        status_color = '\033[92m' if not status else '\033[91m'  # Verde si no tiene el privilegio, Rojo si lo tiene
        print(f"    {privilege}: {status_color}{status}\033[0m")  # \033[0m resetea el color

def print_network_security_info(network_security_info):
    print("Network Security:")
    for item, info in network_security_info.items():
        if item == "Network Interfaces":
            print(f"    {item}:")
            for interface, ipv4_address in info.items():
                print(f"        {interface}: {ipv4_address}")
        elif item == "Open Ports":
            status_color = '\033[91m' if info else '\033[92m'  # Rojo si hay puertos abiertos, Verde si no los hay
            print(f"    {item}: {status_color}{', '.join(map(str, info)) if info else 'None'}\033[0m")
        else:
            status_color = '\033[91m' if info == "Available" else '\033[92m' if info == "Not available" else '\033[94m'  # Rojo si hay conectividad/DNS, Verde si no, Azul para errores
            print(f"    {item}: {status_color}{info}\033[0m")

def check_network_security():
    network_security_info = {
        "Internet Connectivity": "Error",
        "DNS Server": "Error",
        "Network Interfaces": {},
        "Open Ports": []
    }

    # Comprobar conectividad a Internet
    try:
        response = subprocess.check_call(['ping', '-c', '1', '8.8.8.8'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        network_security_info["Internet Connectivity"] = "Available" if response == 0 else "Not available"
    except:
        pass

    # Obtener el servidor DNS
    try:
        with open("/etc/resolv.conf", "r") as resolv_file:
            for line in resolv_file:
                if line.startswith("nameserver"):
                    network_security_info["DNS Server"] = line.split()[1]
                    break
    except:
        pass

    # Listar interfaces de red y direcciones IP
    try:
        interfaces = os.listdir('/sys/class/net/')
        for interface in interfaces:
            ipv4_address_output = subprocess.check_output(['ip', 'addr', 'show', interface], universal_newlines=True)
            if "inet " in ipv4_address_output:
                ipv4_address = ipv4_address_output.split("inet ")[1].split("/")[0]
                network_security_info["Network Interfaces"][interface] = ipv4_address
            else:
                network_security_info["Network Interfaces"][interface] = "No IPv4 address"
    except:
        pass

    # Comprobar puertos abiertos
    for port in range(1, 1024):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.connect(('127.0.0.1', port))
        except socket.error:
            pass
        else:
            network_security_info["Open Ports"].append(port)
        sock.close()

    return network_security_info

def main():
    if not is_docker_environment():
        print("No se encuentra en un entorno Docker. Abortando...")
        sys.exit(1)
    
    isolation_info = check_kernel_isolation()
    print_isolation_info(isolation_info)
    
    print("Comprobando privilegios del usuario...")
    user_privileges_info = check_user_privileges()
    print_user_privileges_info(user_privileges_info)
    
    print("Comprobando seguridad a nivel de red...")
    network_security_info = check_network_security()
    print_network_security_info(network_security_info)

if __name__ == "__main__":
    main()
