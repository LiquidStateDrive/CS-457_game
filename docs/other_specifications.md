# CS 457 Project Concurrency Design

**Student Name:** Eli Povolny  
**Date:** 2026/10/3  
**Course:** CS 457 - Computer Networks  
**Target Server Domain:** `server.povolny.edu`  

---

## Additional specific implementation details

### Program arguments:

#### client.py:

`-h` Displays usage message \
or: \
`-i` Server DNS hostname (required) \
`-p` Server port (required)

#### server.py:

`-h` Displays usage message \
`-p` Listening port (required; binds to `0.0.0.0`).

---

### DNS resolution exception handling

- DNS resolution errors must be caught explicitly
- Output a clear, user-friendly error message advising the user to check their router DNS configuration and exit cleanly with non-zero status code `1`.
- The client application may not directly crash with an unhandled exception and error messages may not be a raw traceback. 

### IO Multiplexing

IO Multiplexing should be handled using selectors, as justified in `concurrency_design.md`