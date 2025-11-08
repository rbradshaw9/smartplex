#!/usr/bin/env python3
"""
Simple runner for SmartPlex API on Railway
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"🚀 Starting SmartPlex API on port {port}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )