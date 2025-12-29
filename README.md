# Laboratory Work №1
## Simple RPC System (Client–Server) using TCP sockets

### Course: Distributed Systems / Computer Networks
### Topic: Remote Procedure Call (RPC), Timeouts, Retries, Failure Handling

---

## Description

This laboratory work implements a **simple RPC (Remote Procedure Call) system** based on **TCP sockets** using **Python**.

The system consists of:
- **RPC Server** — listens for client requests, executes procedures, and returns results.
- **RPC Client** — sends RPC requests to the server, handles timeouts and retries.

The implementation demonstrates:
- Client–server communication over TCP
- JSON-based RPC protocol
- Timeout handling
- Retry mechanism
- Failure scenarios (server delay, dropped responses, blocked port)
- At-least-once and at-most-once semantics using `request_id`

---

## Project Structure

```
rpc-lab1/
│
├── server.py          # RPC Server
├── client.py          # RPC Client
├── README.md          # Documentation
```

---

##️ Technologies Used

- **Python 3.9+**
- **TCP sockets**
- **JSON**
- **UUID (request_id)**
- Python Standard Library only (no external dependencies)

---

## RPC Protocol Format

### Request
```json
{
  "request_id": "uuid-string",
  "method": "add",
  "params": {
    "a": 5,
    "b": 7
  },
  "timestamp": 1730000000
}
```

### Response
```json
{
  "request_id": "uuid-string",
  "status": "OK",
  "result": 12
}
```

---

## Implemented RPC Methods

| Method name | Description | Parameters |
|------------|------------|-----------|
| `add` | Adds two integers | `a`, `b` |
| `reverse_string` | Reverses a string | `s` |
| `get_time` | Returns current UTC time | — |

---

## How to Run (Local)

### Start server
```bash
python3 server.py --host 0.0.0.0 --port 5000
```

### Run client
```bash
python3 client.py --host 127.0.0.1 --port 5000 --method add --a 10 --b 20
```

---

## Timeout & Retries

- Timeout: 2 seconds
- Retries: 2

Total attempts: **3**

---

## Failure Demonstration

### Server delay
```bash
python3 server.py --delay-seconds 5
```

### Drop responses
```bash
python3 server.py --drop-rate 0.7
```

### Firewall block
```bash
sudo ufw deny 5000
```

---

## RPC Semantics

- **At-least-once** — default retry behavior
- **At-most-once** — run server with:
```bash
python3 server.py --at-most-once
```

---

## AWS EC2 Deployment

- Open TCP port 5000
- Run server on EC2 #1
- Run client on EC2 #2

---

## Conclusion

The laboratory work fully demonstrates RPC communication, timeout handling, retries, and failure scenarios.
