#!/usr/bin/env python3
"""
Main Orchestrator for Sannidhay & Pranav's Independent Bot System
================================================================

This script runs the complete workflow:
1. Spencer's Order Extraction Bot (Final_All_Inboxed.py)
2. AI Field Extraction Bot (ai_extract_fields.py) 
3. Patient Creation Bot (Final_patient_bot.py)
4. Signed Document Bot (Final_signed_bot.py)

Usage:
    python main_orchestrator.py [--step STEP_NUMBER]
    
    --step 1: Run only Spencer's Order Extraction
    --step 2: Run only AI Field Extraction  
    --step 3: Run only Patient Creation
    --step 4: Run only Signed Document Extraction
    --step all: Run complete workflow (default)
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

class BotOrchestrator:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.reports_dir = self.base_dir / "Reports"
        self.logs_dir = self.base_dir / "Logs"
        
        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def run_script(self, script_name, description):
        """Run a Python script and handle errors"""
        self.log(f"🚀 Starting {description}")
        script_path = self.base_dir / script_name
        
        try:
            result = subprocess.run([sys.executable, str(script_path)], 
                                  capture_output=True, text=True, cwd=self.base_dir)
            
            if result.returncode == 0:
                self.log(f"✅ {description} completed successfully")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                self.log(f"❌ {description} failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error running {description}: {e}")
            return False
    
    def step_1_spencer_orders(self):
        """Step 1: Extract orders from Athena Inbox"""
        return self.run_script("Final_All_Inboxed.py", "Spencer's Order Extraction Bot")
    
    def step_2_ai_extraction(self):
        """Step 2: Extract fields using AI from the orders"""
        # Find the latest Spencer orders file
        spencer_files = list(self.reports_dir.glob("Spencer_Orders_*.csv"))
        if not spencer_files:
            self.log("❌ No Spencer orders file found. Run step 1 first.")
            return False
            
        latest_file = max(spencer_files, key=lambda f: f.stat().st_mtime)
        self.log(f"📄 Using Spencer orders file: {latest_file.name}")
        
        return self.run_script("ai_extract_fields.py", "AI Field Extraction Bot")
    
    def step_3_patient_creation(self):
        """Step 3: Create patients from failed orders"""
        # Check if we have AI extracted data or create failed_orders.csv
        inbox_dir = self.base_dir / "Inbox"
        inbox_dir.mkdir(exist_ok=True)
        
        failed_orders_file = inbox_dir / "failed_orders.csv"
        if not failed_orders_file.exists():
            self.log("⚠️ No failed_orders.csv found. Creating sample file...")
            # Create a sample failed orders file
            with open(failed_orders_file, 'w') as f:
                f.write("ID,Patient,Status\n")
                f.write("# Add your failed order IDs here\n")
            self.log(f"📝 Created {failed_orders_file}. Please add your failed order data.")
            return False
            
        return self.run_script("Final_patient_bot.py", "Patient Creation Bot")
    
    def step_4_signed_documents(self):
        """Step 4: Extract signed documents"""
        return self.run_script("Final_signed_bot.py", "Signed Document Extraction Bot")
    
    def run_complete_workflow(self):
        """Run the complete workflow"""
        self.log("🎯 Starting Complete Bot Workflow")
        
        steps = [
            (self.step_1_spencer_orders, "Spencer's Order Extraction"),
            (self.step_2_ai_extraction, "AI Field Extraction"),
            (self.step_3_patient_creation, "Patient Creation"),
            (self.step_4_signed_documents, "Signed Document Extraction")
        ]
        
        for i, (step_func, step_name) in enumerate(steps, 1):
            self.log(f"📋 Step {i}: {step_name}")
            success = step_func()
            
            if not success:
                self.log(f"⚠️ Step {i} failed. Stopping workflow.")
                return False
                
        self.log("🎉 Complete workflow finished successfully!")
        return True

def main():
    parser = argparse.ArgumentParser(
        description="Sannidhay & Pranav's Independent Bot System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--step", 
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Which step to run (default: all)"
    )
    
    args = parser.parse_args()
    orchestrator = BotOrchestrator()
    
    if args.step == "1":
        orchestrator.step_1_spencer_orders()
    elif args.step == "2":
        orchestrator.step_2_ai_extraction()
    elif args.step == "3":
        orchestrator.step_3_patient_creation()
    elif args.step == "4":
        orchestrator.step_4_signed_documents()
    else:
        orchestrator.run_complete_workflow()

if __name__ == "__main__":
    main() 