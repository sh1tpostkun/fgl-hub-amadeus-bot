#!/usr/bin/env python3
"""
Main entry point for deployment
"""
import asyncio
import os
import sys

# Add src directory to Python path
sys.path.insert(0, 'src')

from src.bot import main

if __name__ == "__main__":
    asyncio.run(main())
