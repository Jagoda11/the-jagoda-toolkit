#!/bin/bash
# RTK token compression — no-op if rtk binary not installed.
# Install: brew install rtk-ai/tap/rtk
command -v rtk >/dev/null 2>&1 && exec rtk hook claude
exit 0
