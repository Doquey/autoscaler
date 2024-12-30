import re
import docker

def modify_nginx_conf(file_path, server_address, action):
    """
    Modify the nginx configuration file to add or remove a server from the upstream block.

    :param file_path: Path to the .conf file.
    :param server_address: Server address (e.g., 'backend:8001').
    :param action: 'add' to include the server, 'remove' to exclude it.
    """
    global EXITSTING_SERVERS
    with open(file_path, 'r') as file:
        content = file.read()

    upstream_regex = r"(upstream\s+backend_servers\s+\{\s*.*?\})"    
    match_upstream = re.search(upstream_regex, content, re.DOTALL)
    if not match_upstream:
        print("Upstream block not found in the configuration.")
        return

    upstream_block = match_upstream.group(1)

    if action == "add":
        if server_address in upstream_block:
            print(f"Server {server_address} is already in the upstream block.")
            return
        new_upstream_block = re.sub(r"(\{)", f"\\1\n    server {server_address};", upstream_block, 1)
    elif action == "remove":
        new_upstream_block = re.sub(rf"\s*server\s+{re.escape(server_address)};", "", upstream_block)
    else:
        print("Invalid action. Use 'add' or 'remove'.")
        return

    content = content.replace(upstream_block, new_upstream_block)
    with open(file_path, 'w') as file:
        file.write(content)
        
    
    client = docker.from_env()
    container = client.containers.get("autoscaler-web-1")
    exec_command = container.exec_run("nginx -s reload", stderr=True, stdout=True)
    
