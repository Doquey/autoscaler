import requests

def test_server(num_requests=100):
    url = "http://localhost:8080/"
    for i in range(num_requests):
        response = requests.get(url)
        print(f"Request {i+1}: Status Code = {response.status_code}, Time = {response.elapsed.total_seconds()}")

if __name__ == "__main__":
    while True:
        test_server(100)  # Simulate 100 requests
