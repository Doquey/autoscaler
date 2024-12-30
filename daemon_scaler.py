import time
import re
import docker
from collections import defaultdict, deque
import requests
from nginx_utils import modify_nginx_conf
from requests_utils import get_active_requests

# Constants
DATA_UPDATE_TIME = 2  # Interval for checking server load and scaling
MAX_NUM_SERVERS = 10  # Maximum allowed servers
MIN_NUM_SERVERS = 1   # Minimum required servers
BASE_SERVER_ADDRESS = "localhost"
NETWORK_NAME = "autoscaler_mynet"

# Global Variables
CURRENT_PORTS = []
EXISTING_SERVERS = []
SERVER_NAMES = []
SERVERS_LOAD = {}
SERVERS_NAME_PORTS = {}
HISTORIC_REQUESTS_COUNT = defaultdict(deque)

# Utility Functions
def update_servers_control_variables(file_path):
    """Update the global variables tracking existing servers and their ports based on the nginx configuration."""
    global EXISTING_SERVERS, CURRENT_PORTS

    with open(file_path, 'r') as file:
        content = file.read()

    upstream_regex = r"(upstream\s+backend_servers\s+\{\s*.*?\})"
    server_regex = r"server\s+([a-zA-Z0-9_-]+:[0-9]+);"

    match_upstream = re.search(upstream_regex, content, re.DOTALL)
    if not match_upstream:
        print("Upstream block not found in the configuration.")
        return

    upstream_block = match_upstream.group(1)
    match_server = re.findall(server_regex, upstream_block)

    for server in match_server:
        if server not in EXISTING_SERVERS:
            EXISTING_SERVERS.append(server)
            CURRENT_PORTS.append(int(server.split(":")[1]))

def scale_up(container_name, override_command, container_port):
    """Start a new server container and update configuration."""
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        modify_nginx_conf("./lb.conf", f"{container_name}:{container_port}", "remove")
    except docker.errors.NotFound:
        print(f"Container {container_name} not found. Starting a new one.")

    container = client.containers.run(
        image="fastapi-app",
        name=container_name,
        network=NETWORK_NAME,
        ports={f'{container_port}/tcp': container_port},
        command=override_command,
        detach=True
    )

    CURRENT_PORTS.append(container_port)
    SERVERS_LOAD[container_port] = None
    EXISTING_SERVERS.append(f"{container_name}:{container_port}")
    SERVERS_NAME_PORTS[container_port] = container_name

    print(f"Started new container: {container_name} on port {container_port}")
    modify_nginx_conf("./lb.conf", f"{container_name}:{container_port}", "add")

def scale_down(container_name, container_port):
    """Stop and remove a server container and update configuration."""
    print(f"Scaling down server {container_name} on port {container_port}")
    client = docker.from_env()
    container = client.containers.get(container_name)
    container.stop()
    container.remove()

    CURRENT_PORTS.remove(container_port)
    SERVERS_LOAD.pop(container_port)
    SERVERS_NAME_PORTS.pop(container_port)
    EXISTING_SERVERS.remove(f"{container_name}:{container_port}")

    modify_nginx_conf("./lb.conf", f"{container_name}:{container_port}", "remove")

def access_server_and_get_data(server_address, port):
    """Access the server to retrieve load data, retrying if necessary."""
    retries = 5
    for attempt in range(retries):
        try:
            response = requests.get(server_address)
            response.raise_for_status()
            requests_count = get_active_requests(response.text)
            now = time.time()
            HISTORIC_REQUESTS_COUNT[port].append((now, requests_count or 0))

            active_requests = 0
            if len(HISTORIC_REQUESTS_COUNT[port]) > 1:
                time_diff = HISTORIC_REQUESTS_COUNT[port][-1][0] - HISTORIC_REQUESTS_COUNT[port][0][0]
                request_diff = HISTORIC_REQUESTS_COUNT[port][-1][1] - HISTORIC_REQUESTS_COUNT[port][0][1]
                active_requests = request_diff / time_diff
                HISTORIC_REQUESTS_COUNT[port].popleft()

            return active_requests
        except requests.exceptions.RequestException:
            time.sleep(2)

    raise Exception("Failed to connect to server after multiple attempts.")

def update_server_load():
    """Update the load information for all current servers."""
    for port in CURRENT_PORTS:
        server_address = f"http://{BASE_SERVER_ADDRESS}:{port}/metrics"
        active_requests = access_server_and_get_data(server_address, port)
        print(f"Server {port} has {active_requests} active requests.")
        SERVERS_LOAD[port] = active_requests or 0

# Main Function
def main():
    name_counter = 1
    while True:
        print("Checking for scaling up/down")
        update_servers_control_variables("./lb.conf")
        update_server_load()
        time.sleep(DATA_UPDATE_TIME)

        if len(EXISTING_SERVERS) < MAX_NUM_SERVERS:
            valid_loads = {port: load for port, load in SERVERS_LOAD.items() if load is not None}

            if valid_loads:
                if min(valid_loads.values()) > 10:
                    new_port = CURRENT_PORTS[-1] + 1
                    new_backend_name = f"backend_app_{name_counter}"
                    scale_up(new_backend_name, ["python3", "-m", "app.main", "--port", str(new_port), "--name", str(name_counter)], new_port)
                    name_counter += 1
                elif max(valid_loads.values()) < 5 and len(CURRENT_PORTS) > MIN_NUM_SERVERS:
                    valid_loads_no_base = {port: load for port, load in valid_loads.items() if port != CURRENT_PORTS[0]}
                    port_to_remove = min(valid_loads_no_base, key=valid_loads_no_base.get)
                    scale_down(SERVERS_NAME_PORTS[port_to_remove], port_to_remove)
            else:
                print("No valid server load data available.")
        else:
            print("Max number of servers reached. No scaling up is needed.")

if __name__ == "__main__":
    main()
