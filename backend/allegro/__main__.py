"""`python -m allegro`: the API on this computer (`--reload`: restart on every saved change).

The application itself is `allegro.main:app`; in production the server is started by
`uvicorn allegro.main:app` (see start.sh), not through this file.
"""
import os
import sys

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "allegro.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload="--reload" in sys.argv[1:],
    )
