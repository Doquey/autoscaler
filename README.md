# **Autoscaler: Python-Based Load Balancer and Web Server Scaling Solution**

This repository contains a simple autoscaler project, built using Python, NGINX, and Docker. The system functions as a dynamic load balancer and web server provider, designed to handle traffic spikes efficiently by scaling resources up or down as needed.

---

## **How It Works**

### **1. Starting the Base Server**
- The system initializes with a base server configured to use **NGINX** as the Load Balancer.
- The load balancing algorithm used is **`least_conn`**, which directs traffic to servers based on their current request load (i.e., servers with fewer active connections receive more traffic).
- Key ports:
  - **Port 8000**: Base server for handling requests.
  - **Port 8080**: Load Balancer interface for routing requests.

---

### **2. Simulating Traffic**
- A Python script, `simulate_requests.py`, is used to send high volumes of requests to the Load Balancer server at **port 8080**.
- These requests are distributed across the available servers by the Load Balancer.

---

### **3. Autoscaling Mechanism**
- The **autoscaler** dynamically adjusts the number of active servers based on traffic load:
  1. **Scaling Up**:
      - When the number of requests per second (RPS) to a single server exceeds **10**, the autoscaler spawns a new Docker container.
      - The new server runs a copy of the base program and is assigned to the next available port (starting at `BASE_PORT + 1`).
      - Scaling continues until the maximum server limit (10 servers) is reached.
  2. **Scaling Down**:
      - When traffic subsides, the autoscaler monitors the total RPS across all servers.
      - As the RPS drops, the autoscaler removes servers from the pool to optimize resource usage.

---

### **4. Monitoring and Metrics**
- **Prometheus Integration**:
  - The autoscaler monitors server performance using Prometheus metrics exposed by the FastAPI application.
  - A custom endpoint gathers data on the total number of requests processed by each server.
  - This data is analyzed programmatically to determine scaling decisions.

---

### **5. Dynamic NGINX Configuration**
- The autoscaler uses the **Docker SDK for Python** to manage the lifecycle of Docker containers programmatically.
- Updates to the NGINX Load Balancer configuration (`.conf` file) are also handled dynamically by the `daemon_scaler.py` script:
  - Adding new servers to the pool.
  - Removing servers no longer required.

---

## **How to Use**

### **Prerequisites**
- Docker and Docker Compose installed.
- Python 3.8+ installed.
- Prometheus for monitoring.

### **Steps to Run the Autoscaler**
1. **Build and Start Docker Containers**:
   ```bash
   docker build -t fastapi-app .
   docker compose -f docker-compose.yaml up -d
   ```
2. **Start the Autoscaler**:
   ```bash
   screen -dmS daemon_scaler python daemon_scaler.py
   ```
3. **Simulate Traffic**:
   ```bash
   screen -dmS simulate_traffic python simulate_requests.py
   ```
4. **Switch To see Servers Scaling**:
   ```bash
   screen -r daemon_scaler
   ```

### **Stopping the Autoscaler**
- To stop the autoscaler and all active screens:
    **Detach from screen**
    ``` 
    ctrl + a + d

    ```

   ```bash
   screen -ls | grep daemon_scaler | awk '{print $1}' | xargs -I {} screen -S {} -X quit
   ```
   ```
    docker compose down
    docker kill $(docker ps -q)
    ```

---

## **Key Scripts**

### **1. `daemon_scaler.py`**
- Core logic for autoscaling.
- Responsibilities:
  - Monitoring server RPS.
  - Spawning and terminating Docker containers.
  - Dynamically updating the NGINX Load Balancer configuration.

### **2. `simulate_requests.py`**
- Simulates high traffic to the Load Balancer for testing the autoscaling functionality.

---

## **Features**
- Dynamic load balancing using **NGINX**.
- Autoscaling based on RPS thresholds.
- Seamless integration with **Prometheus** for monitoring.
- Docker-based server lifecycle management.

---

## **Future Improvements**
- Implement additional load balancing algorithms.
- Enhance monitoring with Grafana dashboards.
- Optimize autoscaling thresholds for different workloads.
- Add support for Kubernetes as an alternative to Docker Compose.

---

## **Contributing**
Contributions are welcome! Feel free to open issues or submit pull requests for improvements or new features.
