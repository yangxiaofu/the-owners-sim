#!/usr/bin/env python3
"""
Interactive NFL Season Simulation Demo

A terminal-based demo that allows users to simulate an NFL season week-by-week,
displaying game results and standings after each week.

Usage:
    python interactive_season_demo.py
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from demo.interactive_interface import InteractiveInterface


def main():
    """Main entry point for the interactive season demo."""
    print("=" * 60)
    print("🏈 NFL SEASON SIMULATION DEMO")
    print("=" * 60)
    print("Welcome to the interactive NFL season simulator!")
    print("Simulate your season week-by-week and watch the action unfold.")
    print()
    
    try:
        # Initialize and run the interactive demo
        demo = InteractiveInterface()
        demo.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 Thanks for playing! Season simulation ended.")
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        print("Please check your installation and try again.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())